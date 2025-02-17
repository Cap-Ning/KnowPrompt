import os
os.environ['CUDA_VISIBLE_DEVICES']='6'

import torch
from torch.utils.data import DataLoader

from utils import common_load_dataset
from utils import common_load_dnn
from utils import common_tokenize_dataset
from utils import common_split_dataset
from utils import common_decoding

from transformers import Seq2SeqTrainingArguments
from transformers import Seq2SeqTrainer

from src.metrics.bleu import compute_blue_scores

dataset_id = 0
train_data_num = 3000

train_config = {
    'epoch': 100,
    'bsz':  128,
    'lr': 1e-4,
}

train_data, test_data = common_load_dataset(dataset_id)
train_data, _ = common_split_dataset(train_data, train_data_num)


for small_model_id in range(5):
    model, tokenizer = common_load_dnn(small_model_id)
    train_data = common_tokenize_dataset(train_data, tokenizer)
    test_data = common_tokenize_dataset(test_data, tokenizer)

    # Define the training arguments
    training_args = Seq2SeqTrainingArguments(
        predict_with_generate=True,
        evaluation_strategy="steps",
        per_device_train_batch_size=32,
        per_device_eval_batch_size=64,
        num_train_epochs=3,
        save_total_limit=1,
        save_steps=1000,
        logging_steps=1000,
        learning_rate=3e-5,
        warmup_steps=500,
        remove_unused_columns=False,
        output_dir="./output",
    )


    def my_data_collator(batch):
        input_ids = []
        attention_mask = []
        labels = []
        for d in batch:
            input_ids.append(torch.tensor(d['input_ids']))
            attention_mask.append(torch.tensor(d['attention_mask']))
            labels.append(torch.tensor(d['labels']))

        return {
            "input_ids": torch.stack(input_ids),
            "attention_mask": torch.stack(attention_mask),
            "labels": torch.stack(labels),
        }

    # Define the trainer and train the model
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=test_data,
        data_collator=my_data_collator,
        tokenizer=tokenizer,
    )
    trainer.train()
    with torch.no_grad():
        res = trainer.predict(test_data)

    ground_truth = common_decoding(res.label_ids, tokenizer)
    predictions = common_decoding(res.predictions, tokenizer)
    if not os.path.isdir('./tmp'):
        os.mkdir('./tmp')
    s = compute_blue_scores(ground_truth, predictions, './tmp')
    print(small_model_id, s)


