# OptiCart Docker Startup Guide

This guide explains how to run the full app (Django + PostgreSQL) on another machine using Docker Compose.

## 1. Prerequisites

Install these tools first:

- Docker Desktop (or Docker Engine + Compose plugin)
- Git

Check they are installed:

```bash
docker --version
docker compose version
git --version
```

## 2. Get the project

```bash
git clone <your-repo-url>
cd OptiCart
```

## 3. Create environment file

Create a local environment file from the template:

```bash
cp .env.dev .env
```

You can keep defaults for local development, or edit `.env` if needed.

Required values are already present in `.env.dev`:

- DB_ENGINE=postgres
- POSTGRES_DB=opticart_db
- POSTGRES_USER=opticart_user
- POSTGRES_PASSWORD=opticart_password
- POSTGRES_HOST=localhost
- POSTGRES_PORT=5432

Note: inside Docker, the web container uses `postgres` as DB host automatically via Compose.

## 4. Build and start containers

```bash
docker compose up -d --build
```

This starts:

- `postgres` container (database)
- `web` container (Django app)

## 5. Verify everything is running

```bash
docker compose ps
```

Expected:

- `postgres` is Up (healthy)
- `web` is Up

Check web logs if needed:

```bash
docker compose logs -f web
```

## 6. Open the app

Open in browser:

- http://localhost:8000

## 7. Product images are applied automatically

On container startup, the app automatically runs:

- migrations
- image URL import from `product_images.txt` (if that file exists)

So normally you do not need any extra image command.

Manual fallback (if needed):

```bash
docker compose exec web python manage.py update_product_images --file product_images.txt
```

## 8. Useful commands

Stop containers:

```bash
docker compose down
```

Stop and remove DB data volume (full reset):

```bash
docker compose down -v
```

Rebuild after code/dependency changes:

```bash
docker compose up -d --build
```

Run migrations manually:

```bash
docker compose exec web python manage.py migrate
```

Open Django shell:

```bash
docker compose exec web python manage.py shell
```

## 9. Troubleshooting

Port 8000 already in use:

- Stop the process using port 8000, or change mapping in `docker-compose.yml` from `8000:8000` to another host port (for example `8080:8000`).

Port 5432 already in use:

- Stop local PostgreSQL, or change the host port mapping in `docker-compose.yml`.

Web container restarting:

```bash
docker compose logs --tail=200 web
```

Database connection errors:

- Wait until postgres becomes healthy (`docker compose ps`)
- Restart web container:

```bash
docker compose restart web
```
