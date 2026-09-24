import torch

print('torch:', torch.__version__)
print('cuda available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('cuda runtime:', torch.version.cuda)
    print('gpu:', torch.cuda.get_device_name(0))
    props = torch.cuda.get_device_properties(0)
    print('VRAM GiB:', round(props.total_memory / 1024**3, 2))
    print('bf16 supported:', torch.cuda.is_bf16_supported())
