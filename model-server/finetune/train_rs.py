"""QLoRA adaptation for curated RS image/question/answer JSONL on a free T4 GPU.

This is a training entry point, NOT pretrained weights or an evaluation claim.
Each row: {scene_id, source, images: [path, ...], question, answer}.
Use only training and validation splits; never supply benchmark test annotations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def read_records(path: Path) -> list[dict]:
    records = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        for key in ('scene_id', 'source', 'images', 'question', 'answer'):
            if not row.get(key):
                raise ValueError(f'{path}:{number}: missing {key}')
        if not isinstance(row['images'], list) or not 1 <= len(row['images']) <= 2:
            raise ValueError(f'{path}:{number}: require one or two images')
        row['images'] = [str((path.parent / image).resolve()) for image in row['images']]
        if any(not Path(image).is_file() for image in row['images']):
            raise ValueError(f'{path}:{number}: image does not exist')
        records.append(row)
    if not records:
        raise ValueError('Dataset is empty')
    return records


def check_splits(train: list[dict], validation: list[dict]):
    train_scenes = {row['scene_id'] for row in train}
    val_scenes = {row['scene_id'] for row in validation}
    if train_scenes & val_scenes:
        raise ValueError('Scene leakage between train and validation; split by geographic scene.')
    def hashes(rows):
        return {hashlib.sha256(Path(image).read_bytes()).hexdigest() for row in rows for image in row['images']}
    if hashes(train) & hashes(validation):
        raise ValueError('Identical image content appears in both splits.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', required=True, type=Path)
    parser.add_argument('--validation', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model', default='Qwen/Qwen2.5-VL-7B-Instruct')
    parser.add_argument('--epochs', type=float, default=1)
    parser.add_argument('--max-steps', type=int, default=-1)
    args = parser.parse_args()
    train, validation = read_records(args.train), read_records(args.validation)
    check_splits(train, validation)

    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration, BitsAndBytesConfig, Trainer, TrainingArguments, set_seed
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    if not torch.cuda.is_available():
        raise RuntimeError('Select a GPU runtime in Colab/Kaggle. QLoRA requires CUDA here.')
    set_seed(42)
    processor = AutoProcessor.from_pretrained(args.model, min_pixels=128 * 28 * 28, max_pixels=256 * 28 * 28)
    processor.tokenizer.padding_side = 'right'
    bf16 = torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if bf16 else torch.float16
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(args.model,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype),
        device_map={'': 0}, torch_dtype=dtype, attn_implementation='sdpa')
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=.05,
        target_modules=['q_proj', 'v_proj'], task_type='CAUSAL_LM'))
    model.config.use_cache = False

    def collate(rows):
        # Batch size 1 avoids ambiguous alignment of multiple vision token sequences.
        row = rows[0]
        images = []
        for path in row['images']:
            with Image.open(path) as image:
                images.append(image.convert('RGB'))
        messages = [{'role': 'system', 'content': 'You are a remote-sensing analyst. Answer from the supplied observations and state uncertainty.'},
            {'role': 'user', 'content': [*({'type': 'image'} for _ in images), {'type': 'text', 'text': row['question']}]}]
        prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        full = processor.apply_chat_template([*messages, {'role': 'assistant', 'content': row['answer']}], tokenize=False)
        encoded = processor(text=[full], images=images, return_tensors='pt', padding=True)
        prefix = processor(text=[prompt], images=images, return_tensors='pt')
        if encoded['input_ids'].shape[1] > 4096:
            raise ValueError('Example exceeds 4096 tokens. Shorten text; never truncate vision tokens.')
        labels = encoded['input_ids'].clone()
        prefix_length = prefix['input_ids'].shape[1]
        if not torch.equal(encoded['input_ids'][0, :prefix_length], prefix['input_ids'][0]):
            raise ValueError('Chat template prefix mismatch; cannot safely mask training labels.')
        labels[:, :prefix_length] = -100
        labels[encoded['attention_mask'] == 0] = -100
        if not (labels != -100).any():
            raise ValueError('No answer tokens remain after masking.')
        encoded['labels'] = labels
        return encoded

    trainer = Trainer(model=model, args=TrainingArguments(output_dir=str(args.output),
        per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=16,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        learning_rate=1e-4, num_train_epochs=args.epochs, max_steps=args.max_steps,
        fp16=not bf16, bf16=bf16, logging_steps=5, save_steps=100, save_total_limit=2,
        eval_strategy='epoch', report_to='none', remove_unused_columns=False,
        optim='paged_adamw_8bit', seed=42),
        train_dataset=train, eval_dataset=validation, data_collator=collate)
    trainer.train()
    metrics = trainer.evaluate()
    model.save_pretrained(args.output)
    processor.save_pretrained(args.output)
    manifest = {'base_model': args.model, 'method': 'QLoRA', 'seed': 42,
        'sources': sorted({row['source'] for row in train}), 'train_examples': len(train),
        'validation_examples': len(validation), 'train_sha256': hashlib.sha256(args.train.read_bytes()).hexdigest(),
        'validation_sha256': hashlib.sha256(args.validation.read_bytes()).hexdigest(),
        'metrics': metrics, 'benchmark_status': 'not_evaluated',
        'limitations': 'Adapter trained on prepared display imagery; does not calibrate SAR or multispectral radiometry.'}
    (args.output / 'adaptation_manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Adapter saved. Run prescribed held-out benchmarks before deployment.')


if __name__ == '__main__':
    main()
