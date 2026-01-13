# Usar una imagen base de Python oficial más moderna
FROM python:3.11-slim

# Instalar dependencias del sistema requeridas (FFmpeg)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de requisitos
COPY requirements.txt .

# Instalar las dependencias de Python
# Añadimos gunicorn directamente por si no está en requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# Copiar el resto del código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p downloads bin

# Exponer el puerto
EXPOSE 5000

# Comando para ejecutar la aplicación usando Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]
