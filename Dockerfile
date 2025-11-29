FROM python:3.14

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code

RUN pip install poetry

WORKDIR /code

COPY pyproject.toml /code/
COPY . /code/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root
