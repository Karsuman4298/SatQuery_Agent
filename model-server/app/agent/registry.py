"""Observable capability constraints; model text cannot expand this registry."""
REGISTRY = {
    'vqa': {'required': ('image',), 'description': 'VQA and scene description from display previews'},
    'segmentation': {'required': ('image',), 'description': 'Text/point localization and MobileSAM mask'},
    'change_detection': {'required': ('before', 'after'), 'description': 'Paired VLM description and exploratory RGB difference'},
    'fusion': {'required': ('optical', 'sar'), 'description': 'Joint optical–SAR visual interpretation; not calibrated sensor fusion'},
    'conversational': {'required': (), 'description': 'Context and clarification'},
}


def missing_inputs(task, context):
    if task not in REGISTRY:
        raise ValueError('Unknown specialist task')
    return [key for key in REGISTRY[task]['required'] if not context.get(key)]
