document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const searchBtn = document.getElementById('searchBtn');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const errorText = document.getElementById('errorText');
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadStatus = document.getElementById('downloadStatus');

    // New elements
    const qualityContainer = document.getElementById('qualityContainer');
    const qualitySelect = document.getElementById('qualitySelect');
    const formatRadios = document.querySelectorAll('input[name="format"]');

    // Elements to fill
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const videoDuration = document.getElementById('videoDuration');
    const platformTag = document.getElementById('platformTag');

    searchBtn.addEventListener('click', fetchVideoInfo);
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchVideoInfo();
    });

    downloadBtn.addEventListener('click', downloadVideo);

    // Toggle quality selector based on format
    formatRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'audio') {
                qualityContainer.style.display = 'none';
            } else {
                qualityContainer.style.display = 'block';
            }
        });
    });

    async function fetchVideoInfo() {
        const url = urlInput.value.trim();
        if (!url) return;

        showLoading(true);
        hideError();
        resultDiv.classList.add('hidden');

        try {
            const response = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch video info');
            }

            displayResult(data);
        } catch (err) {
            showError(err.message);
        } finally {
            showLoading(false);
        }
    }

    function displayResult(data) {
        thumbnail.src = data.thumbnail;
        videoTitle.textContent = data.title;
        videoDuration.innerHTML = `<i class="fa-regular fa-clock"></i> ${formatDuration(data.duration)}`;
        platformTag.textContent = data.extractor || 'Web';

        resultDiv.classList.remove('hidden');
    }

    async function downloadVideo() {
        const url = urlInput.value.trim();
        const format = document.querySelector('input[name="format"]:checked').value;
        const quality = qualitySelect.value;
        const button = downloadBtn;
        const statusMessage = document.getElementById('statusMessage');
        const statusDetail = document.getElementById('statusDetail');

        if (!url) return;

        // Visual feedback
        button.disabled = true;
        downloadStatus.classList.remove('hidden');
        button.style.opacity = '0.7';
        hideError();

        // Progress messages
        const messages = [
            { msg: 'Conectando con el servidor...', detail: 'Iniciando descarga', time: 0 },
            { msg: 'Descargando video...', detail: 'Esto puede tardar varios minutos para videos largos', time: 3000 },
            { msg: 'Procesando archivo...', detail: 'Casi listo...', time: 8000 }
        ];

        let messageIndex = 0;
        const messageInterval = setInterval(() => {
            if (messageIndex < messages.length) {
                statusMessage.textContent = messages[messageIndex].msg;
                statusDetail.textContent = messages[messageIndex].detail;
                messageIndex++;
            }
        }, 3000);

        // Simulate progress bar
        const progressFill = document.querySelector('.progress-fill');
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 10;
                progressFill.style.width = Math.min(progress, 90) + '%';
            }
        }, 500);

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, format, quality })
            });

            clearInterval(messageInterval);
            clearInterval(progressInterval);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Download failed');
            }

            // Complete progress
            progressFill.style.width = '100%';
            statusMessage.textContent = '¡Descarga completa!';
            statusDetail.textContent = 'Guardando archivo...';

            // Handle blob download
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;

            // Extract filename from header if available, or default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'download';
            if (contentDisposition) {
                const matches = /filename="?([^"]+)"?/.exec(contentDisposition);
                if (matches && matches[1]) {
                    filename = matches[1];
                }
            } else {
                filename = `download.${format === 'audio' ? 'mp3' : 'mp4'}`;
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            // Success feedback
            setTimeout(() => {
                downloadStatus.classList.add('hidden');
                progressFill.style.width = '0%';
            }, 2000);

        } catch (err) {
            clearInterval(messageInterval);
            clearInterval(progressInterval);
            progressFill.style.width = '0%';
            showError("Error al descargar: " + err.message);
        } finally {
            button.disabled = false;
            button.style.opacity = '1';
        }
    }

    function showLoading(show) {
        if (show) loadingDiv.classList.remove('hidden');
        else loadingDiv.classList.add('hidden');
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorDiv.classList.remove('hidden');
    }

    function hideError() {
        errorDiv.classList.add('hidden');
    }

    function formatDuration(seconds) {
        if (!seconds) return 'Live/Unknown';
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }
});
