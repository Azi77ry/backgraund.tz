document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const loading = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const errorMsg = document.getElementById('error-message');
    const originalImg = document.getElementById('original-image');
    const resultImg = document.getElementById('result-image');
    const downloadBtn = document.getElementById('download-btn');
    const newBtn = document.getElementById('new-image-btn');
    const progressBar = document.getElementById('progress-bar');

    // Event Listeners
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    newBtn.addEventListener('click', resetUI);

    // Drag and Drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileSelect({ target: { files: e.dataTransfer.files } });
        }
    });

    // Functions
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
            showError('Only PNG, JPG, and WEBP files are allowed');
            return;
        }

        if (file.size > 16 * 1024 * 1024) {
            showError('File size must be less than 16MB');
            return;
        }

        resetUI();
        showPreview(file);
        uploadFile(file);
    }

    function showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            originalImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    function uploadFile(file) {
        loading.style.display = 'flex';
        progressBar.style.width = '0%';

        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/remove-bg', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = `${percent}%`;
            }
        };

        xhr.onload = () => {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        showResult(response);
                    } else {
                        showError(response.error || 'Processing failed');
                    }
                } catch (e) {
                    showError('Invalid server response');
                }
            } else {
                showError(`Error: ${xhr.statusText}`);
            }
            loading.style.display = 'none';
        };

        xhr.onerror = () => {
            showError('Network error');
            loading.style.display = 'none';
        };

        xhr.send(formData);
    }

    function showResult(response) {
        resultImg.src = response.result;
        downloadBtn.href = response.download;
        document.getElementById('results').style.display = 'block';
    }

    function showError(message) {
        errorMsg.textContent = message;
        errorDiv.style.display = 'block';
        loading.style.display = 'none';
    }

    function resetUI() {
        fileInput.value = '';
        errorDiv.style.display = 'none';
        document.getElementById('results').style.display = 'none';
        progressBar.style.width = '0%';
    }
});