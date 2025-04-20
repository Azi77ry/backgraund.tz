document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const errorDiv = document.getElementById('error');
    const originalImage = document.getElementById('original-image');
    const resultImage = document.getElementById('result-image');
    const downloadBtn = document.getElementById('download-btn');
    const newImageBtn = document.getElementById('new-image-btn');
    const errorMessage = document.getElementById('error-message');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const originalInfo = document.getElementById('original-info');
    const resultInfo = document.getElementById('result-info');
    const currentYear = document.getElementById('current-year');

    // Set current year in footer
    currentYear.textContent = new Date().getFullYear();

    // File validation
    const validTypes = ['image/png', 'image/jpeg', 'image/webp'];
    const maxSize = 16 * 1024 * 1024; // 16MB

    // Event Listeners
    uploadBtn.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Button events
    newImageBtn.addEventListener('click', resetForm);
    
    // Functions
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) processFile(file);
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('highlight');
    }

    function handleDragLeave() {
        uploadArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('highlight');
        
        const file = e.dataTransfer.files[0];
        if (file) processFile(file);
    }

    function processFile(file) {
        // Validate file
        if (!validTypes.includes(file.type)) {
            showError('Invalid file type. Please upload a PNG, JPG, or WEBP image.');
            return;
        }

        if (file.size > maxSize) {
            showError('File is too large. Maximum size is 16MB.');
            return;
        }

        // Reset UI
        resetUI();
        
        // Display file info
        displayFileInfo(file, originalInfo);
        
        // Show preview of original image
        const reader = new FileReader();
        reader.onload = (e) => {
            originalImage.src = e.target.result;
        };
        reader.readAsDataURL(file);

        // Prepare for upload
        loading.style.display = 'block';
        progressContainer.style.display = 'block';
        
        // Upload file
        uploadFile(file);
    }

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        
        // Progress tracking
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
            }
        });

        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                progressContainer.style.display = 'none';
                
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            handleSuccess(response);
                        } else {
                            showError(response.error || 'Failed to process image');
                        }
                    } catch (e) {
                        showError('Invalid response from server');
                        console.error('Error parsing response:', e);
                    }
                } else {
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        showError(errorResponse.error || 'Server error occurred');
                    } catch (e) {
                        showError(`Error ${xhr.status}: ${xhr.statusText}`);
                    }
                }
            }
        };

        xhr.open('POST', '/remove-bg', true);
        xhr.send(formData);
    }

    function handleSuccess(data) {
        // Display results
        resultImage.src = data.result;
        downloadBtn.href = data.download;
        
        // Show file size information if available
        if (data.result) {
            fetch(data.result)
                .then(res => res.blob())
                .then(blob => {
                    resultInfo.textContent = formatFileInfo(blob.size);
                });
        }
        
        loading.style.display = 'none';
        results.style.display = 'block';
        uploadArea.style.display = 'none';
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
        loading.style.display = 'none';
        progressContainer.style.display = 'none';
    }

    function resetUI() {
        errorDiv.style.display = 'none';
        results.style.display = 'none';
        progressBar.style.width = '0%';
        originalInfo.textContent = '';
        resultInfo.textContent = '';
        uploadArea.style.display = 'flex'; // Show upload area again
    }

    function resetForm() {
        fileInput.value = '';
        resetUI();
        originalImage.src = '';
        resultImage.src = '';
        downloadBtn.href = '#';
    }

    function displayFileInfo(file, element) {
        element.textContent = formatFileInfo(file.size);
    }

    function formatFileInfo(bytes) {
        if (bytes < 1024) return `Size: ${bytes} bytes`;
        if (bytes < 1024 * 1024) return `Size: ${(bytes / 1024).toFixed(1)} KB`;
        return `Size: ${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
});