"""Run TextFooler against a classifier exposed locally or via cloud APIs."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

from textattack import Attacker, AttackArgs
from textattack.attack_recipes import TextFoolerJin2019
from textattack.datasets import Dataset

from .hf_inference_wrapper import HFInferenceAPIWrapper
from .model_wrapper import HFModelWrapper
from .yandex_cloud_wrapper import YandexCloudClassifierWrapper


os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def load_csv_dataset(path: Path, max_examples: int | None = None):
    examples = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if "text" not in reader.fieldnames or "label" not in reader.fieldnames:
            raise ValueError(
                f"CSV must contain 'text' and 'label' columns, got: {reader.fieldnames}"
            )
        for row in reader:
            label = int(row["label"])
            examples.append((row["text"], label))
            if max_examples and len(examples) >= max_examples:
                break
    return examples


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="/home/unqual/models/my-llm",
        help="Either a local model directory or a Hugging Face Hub repo id (e.g., user/model)",
    )
    parser.add_argument(
        "--data",
        default="data/test.csv",
        help="CSV file with two columns: text,label",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=100,
        help="Maximum number of examples to attack",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Force computation device",
    )
    parser.add_argument(
        "--query-budget",
        type=int,
        default=1000,
        help="Maximum model queries per example",
    )
    parser.add_argument(
        "--log-csv",
        default="attacks_results.csv",
        help="Where to store attack logs",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="Tokenizer max_length passed to the wrapper",
    )
    parser.add_argument(
        "--hf-token",
        default=os.getenv("HF_TOKEN"),
        help="Optional Hugging Face access token for private repos (or set HF_TOKEN env)",
    )
    backend_group = parser.add_argument_group("Model backend options")
    backend_group.add_argument(
        "--use-inference-api",
        action="store_true",
        help="Use Hugging Face Inference API instead of downloading model weights",
    )
    backend_group.add_argument(
        "--labels",
        default=None,
        help="Comma-separated label order for inference API (e.g., LABEL_0,LABEL_1)",
    )
    backend_group.add_argument(
        "--use-yandex-cloud",
        action="store_true",
        help="Query Yandex Cloud completion endpoint as a classifier",
    )
    backend_group.add_argument(
        "--yc-model",
        default="yandexgpt-lite",
        help="Yandex Cloud model slug (e.g., yandexgpt-lite or yandexgpt)",
    )
    backend_group.add_argument(
        "--yc-labels",
        default="0,1",
        help="Comma-separated label order expected from the cloud classifier",
    )
    backend_group.add_argument(
        "--yc-system-prompt",
        default=None,
        help="Override default system prompt for Yandex Cloud classifier",
    )
    backend_group.add_argument(
        "--yc-temperature",
        type=float,
        default=0.2,
        help="Temperature for Yandex Cloud completion",
    )
    backend_group.add_argument(
        "--yc-max-tokens",
        type=int,
        default=200,
        help="Max tokens for Yandex Cloud completion",
    )
    backend_group.add_argument(
        "--yc-timeout",
        type=int,
        default=30,
        help="Request timeout for Yandex Cloud calls (seconds)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    backends_selected = sum(
        int(flag)
        for flag in (args.use_inference_api, args.use_yandex_cloud)
    )
    if backends_selected > 1:
        raise ValueError("Choose only one backend mode (local/HF hub, inference API, Yandex Cloud)")

    if args.use_yandex_cloud:
        labels = [s.strip() for s in args.yc_labels.split(",") if s.strip()]
        model = YandexCloudClassifierWrapper(
            labels=labels,
            model=args.yc_model,
            system_prompt=args.yc_system_prompt,
            temperature=args.yc_temperature,
            max_tokens=args.yc_max_tokens,
            request_timeout=args.yc_timeout,
        )
    elif args.use_inference_api:
        labels = [s.strip() for s in args.labels.split(",")] if args.labels else None
        model = HFInferenceAPIWrapper(
            model_id=args.model,
            token=args.hf_token,
            labels=labels,
        )
    else:
        model = HFModelWrapper(
            args.model,
            device=args.device,
            max_length=args.max_length,
            hf_token=args.hf_token,
        )

    dataset_path = Path(args.data)
    examples = load_csv_dataset(dataset_path, max_examples=args.num_examples)
    if not examples:
        raise RuntimeError("Dataset is empty; nothing to attack.")

    dataset = Dataset(examples)
    attack = TextFoolerJin2019.build(model)

    attack_args = AttackArgs(
        num_examples=len(examples),
        query_budget=args.query_budget,
        log_to_csv=args.log_csv,
        csv_coloring_style="plain",
        disable_stdout=False,
        shuffle=False,
        parallel=False,
        random_seed=42,
    )

    attacker = Attacker(attack, dataset, attack_args)
    attacker.attack_dataset()


if __name__ == "__main__":
    main()
