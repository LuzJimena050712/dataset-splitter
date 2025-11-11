const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const configSection = document.getElementById('configSection');
const processBtn = document.getElementById('processBtn');
const loading = document.getElementById('loading');
const errorEl = document.getElementById('error');
const resultsSection = document.getElementById('resultsSection');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

fileInput.addEventListener('change', function() {
    if (this.files.length > 0) {
        const file = this.files[0];
        if (!file.name.endsWith('.arff')) {
            showError('Por favor selecciona un archivo .arff válido');
            this.value = '';
            return;
        }
        
        // Verificar tamaño
        const sizeMB = file.size / (1024 * 1024);
        if (sizeMB > 50) {
            showError(`Archivo muy grande (${sizeMB.toFixed(1)}MB). Máximo 50MB`);
            this.value = '';
            return;
        }
        
        fileName.textContent = `${file.name} (${sizeMB.toFixed(2)}MB)`;
        configSection.classList.remove('hidden');
    } else {
        fileName.textContent = 'Sin archivos seleccionados';
        configSection.classList.add('hidden');
    }
});

document.getElementById('valSize').addEventListener('input', function() {
    const valSize = parseInt(this.value) || 0;
    const trainSize = 60;
    const testSize = 100 - trainSize - valSize;
    if (testSize < 10 || testSize > 40) {
        this.value = 20;
        document.getElementById('testSize').value = 20;
        return;
    }
    document.getElementById('testSize').value = testSize;
});

processBtn.addEventListener('click', processDataset);

downloadBtn.addEventListener('click', function() {
    window.location = '/download/';
});

resetBtn.addEventListener('click', function() {
    fileInput.value = '';
    fileName.textContent = 'Sin archivos seleccionados';
    document.getElementById('valSize').value = 20;
    document.getElementById('testSize').value = 20;
    document.getElementById('randomState').value = 42;
    hideAll();
});

async function processDataset() {
    const file = fileInput.files[0];
    if (!file) {
        showError('Por favor selecciona un archivo');
        return;
    }
    
    hideAll();
    loading.classList.remove('hidden');
    processBtn.disabled = true;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('random_state', document.getElementById('randomState').value || '42');
    
    try {
        // Timeout aumentado a 2 minutos para Render Free tier
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        
        const response = await fetch('/split/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (response.ok && data.ok) {
            displayResults(data);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            showError(' El servidor tardó demasiado. Si es la primera vez, espera 1 minuto y vuelve a intentar (el servidor está "despertando").');
        } else {
            showError('Error al procesar el archivo: ' + err.message);
        }
        configSection.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
        processBtn.disabled = false;
    }
}

function displayResults(data) {
    document.getElementById('statOriginal').textContent = (data.stats.total || 0).toLocaleString();
    document.getElementById('statTrain').textContent = (data.stats.train_count || 0).toLocaleString();
    document.getElementById('statVal').textContent = (data.stats.val_count || 0).toLocaleString();
    document.getElementById('statTest').textContent = (data.stats.test_count || 0).toLocaleString();
    
    document.getElementById('statTrainPct').textContent = '60';
    document.getElementById('statValPct').textContent = '20';
    document.getElementById('statTestPct').textContent = '20';
    
    resultsSection.classList.remove('hidden');
    downloadBtn.disabled = false;
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    setTimeout(() => {
        errorEl.classList.add('hidden');
    }, 8000);
}

function hideAll() {
    loading.classList.add('hidden');
    errorEl.classList.add('hidden');
    resultsSection.classList.add('hidden');
    downloadBtn.disabled = true;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    if (!cookieValue) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            cookieValue = csrfToken.value;
        }
    }
    return cookieValue;
}