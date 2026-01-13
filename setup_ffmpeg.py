import os
import zipfile
import shutil
import urllib.request
import sys

# Using a stable FFmpeg essentials build URL
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
BIN_DIR = "bin"

def install_ffmpeg():
    if os.path.exists(os.path.join(BIN_DIR, "ffmpeg.exe")) and os.path.exists(os.path.join(BIN_DIR, "ffprobe.exe")):
        print("[INFO] FFmpeg ya esta instalado.")
        return True

    print("[INFO] FFmpeg no encontrado. Descargando (esto puede tardar unos minutos)...")
    
    if not os.path.exists(BIN_DIR):
        os.makedirs(BIN_DIR)

    zip_path = "ffmpeg.zip"
    
    try:
        # Download with progress bar
        def reporthook(blocknum, blocksize, totalsize):
            readsofar = blocknum * blocksize
            if totalsize > 0:
                percent = readsofar * 1e2 / totalsize
                s = "\r%5.1f%% %*d / %d" % (
                    percent, len(str(totalsize)), readsofar, totalsize)
                sys.stderr.write(s)
                if readsofar >= totalsize:
                    sys.stderr.write("\n")
            else:
                sys.stderr.write("\rDescargando... %d bytes" % readsofar)

        print(f"[INFO] Descargando desde: {FFMPEG_URL}")
        urllib.request.urlretrieve(FFMPEG_URL, zip_path, reporthook)
        print("\n[INFO] Descarga completada. Extrayendo...")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Look for the bin folder inside the zip
            for file in zip_ref.namelist():
                if file.endswith("ffmpeg.exe") or file.endswith("ffprobe.exe"):
                    print(f"[INFO] Extrayendo {os.path.basename(file)}...")
                    source = zip_ref.open(file)
                    target = open(os.path.join(BIN_DIR, os.path.basename(file)), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
        
        print("[INFO] FFmpeg instalado correctamente.")
        return True
    
    except Exception as e:
        print(f"[ERROR] Fallo al instalar FFmpeg: {str(e)}")
        print("[WARNING] La aplicacion funcionara con formatos limitados.")
        return False
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    install_ffmpeg()
