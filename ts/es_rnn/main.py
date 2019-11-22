import os
import time
from pathlib import Path

import pandas as pd
import torch
from torch.nn import SmoothL1Loss
from torch.utils.data import DataLoader

from ts.es_rnn.config import get_config
from ts.es_rnn.data_loading import SeriesDataset
from ts.es_rnn.model import ESRNN
from ts.es_rnn.trainer import ESRNNTrainer
from ts.utils.helper_funcs import MODEL_TYPE, set_seed, create_datasets
from ts.utils.loss_modules import PinballLoss

set_seed(0)

run_id = str(int(time.time()))
print("Starting run={}, model={} ".format(run_id, MODEL_TYPE.ESRNN))

try:
    user_paths = os.environ["PYTHONPATH"].split(os.pathsep)
    print(user_paths)
except KeyError:
    user_paths = []

BASE_DIR = Path("data/raw/")
LOG_DIR = Path("logs/" + MODEL_TYPE.ESRNN.name)
FIGURE_PATH = Path("figures-temp/" + MODEL_TYPE.ESRNN.name)

print("loading config")
config = get_config("Quarterly")

print("loading data")
info = pd.read_csv(str(BASE_DIR / "M4info.csv"))

train_path = str(BASE_DIR / "train/%s-train.csv") % (config["variable"])
test_path = str(BASE_DIR / "test/%s-test.csv") % (config["variable"])

sample = config["sample"]
sample_ids = config["sample_ids"] if "sample_ids" in config else []
train, ts_labels, val, test, test_idx = create_datasets(train_path, test_path, config["output_size"], sample_ids,
                                                        sample=sample)
print("#of train ts:{}, dimensions of validation ts:{}, dimensions of test ts:{}".format(train.shape, val.shape,
                                                                                         test.shape))

dataset = SeriesDataset(train, val, test, info, config["variable"], config["chop_val"], config["device"],
                        ts_labels, sample)
config["num_of_categories"] = len(dataset.dataInfoCatHeaders)
dataloader = DataLoader(dataset, batch_size=config["batch_size"], shuffle=True)

model = ESRNN(num_series=len(dataset), config=config)
reload = config["reload"]
add_run_id = config["add_run_id"]
optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
#criterion = PinballLoss(config["training_tau"], config["output_size"] * config["batch_size"], config["device"])
criterion = SmoothL1Loss()
tr = ESRNNTrainer(MODEL_TYPE.ESRNN.name, model, optimizer, criterion, dataloader, run_id, add_run_id, config,
                  ohe_headers=dataset.dataInfoCatHeaders,
                  csv_path=LOG_DIR,
                  figure_path=FIGURE_PATH, sampling=sample, reload=reload)
tr.train_epochs()
