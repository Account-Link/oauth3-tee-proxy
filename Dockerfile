FROM python:3.11-slim

RUN pip install uv
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /root/

ADD requirements.txt ./
RUN pip install -r requirements.txt

ADD main.py ./
ADD patches.py ./
ADD twitter_client.py ./
ADD models.py ./
ADD config.py ./
ADD safety.py ./
ADD database.py ./
ADD telegram_client.py ./
ADD telegram_routes.py ./
ADD webauthn_routes.py ./

# Add template and static directories
ADD templates/ ./templates/
ADD static/ ./static/

CMD [ "uv", "run", "main.py" ]