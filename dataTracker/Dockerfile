FROM python:3.11-slim

WORKDIR /home/dataTracker

COPY --chown=dataTracker:dataTracker . .

RUN groupadd -r dataTracker && \
    useradd --create-home --home /home/dataTracker -r -g dataTracker dataTracker && \
    python3 -m pip install -r requirements.txt

USER dataTracker

CMD ["python", "./dataTracker/main.py"]
