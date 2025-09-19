# Adversarial attack helpers

This package contains a minimal TextAttack integration for running a TextFooler
attack against different deployment options of a sequence classification model.

Usage examples

- Local model directory (downloaded weights):
  `python -m adversarial_attacks.run_attack --model /path/to/model_dir --data data/test.csv`

- Cloud (Hugging Face Hub) model by repo id:
  `python -m adversarial_attacks.run_attack --model user/model --data data/test.csv`

If the Hub repo is private, provide a token via `--hf-token` or env `HF_TOKEN`.

- Cloud without downloading weights (Inference API):
  `python -m adversarial_attacks.run_attack --use-inference-api --model user/model --data data/test.csv --labels LABEL_0,LABEL_1`

- Yandex Cloud foundation model as classifier:
  `python -m adversarial_attacks.run_attack --use-yandex-cloud --data data/test.csv --yc-labels 0,1`
  (требуются переменные окружения `FOLDER_ID`, `KEY_ID`, `SERVICE_ACCOUNT_ID` и приватный ключ, который
  уже используется ботом; при необходимости переопределите промпт через `--yc-system-prompt`).

Notes
- Inference API wrapper expects a text-classification endpoint returning labels and scores.
- For consistent logits, pass `--labels` to fix label order; otherwise it infers from the first response.
- Для Yandex Cloud по умолчанию используется промпт, заставляющий модель вернуть JSON с вероятностями
  классов `0` и `1`. Убедитесь, что ваш промпт/модель действительно выдаёт такие данные, иначе
  адаптируйте параметры `--yc-system-prompt` и `--yc-labels`.
