const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const configSection = document.getElementById('configSection');
const processBtn = document.getElementById('processBtn');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const resultsSection = document.getElementById('resultsSection');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

let sessionId = null;

fileInput.addEventListener('change', function() {
    if (this.files.length > 0) {
        const file = this.files[0];
        if (!file.name.endsWith('.arff')) {
            showError('Por favor selecciona un archivo .arff válido');
            this.value = '';
            return;
        }
        fileName.textContent = file.name;
        configSection.classList.remove('hidden');
    } else {
        fileName.textContent = 'Sin archivos seleccionados';
        configSection.classList.add('hidden');
    }
});

document.getElementById('valSize').addEventListener('input', function() {
    const valSize = parseInt(this.value);
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
    if (sessionId) {
        window.location.href = `/download/?session_id=${sessionId}`;
    }
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
    
    const trainSize = parseInt(document.getElementById('trainSize').value);
    const valSize = parseInt(document.getElementById('valSize').value);
    const testSize = parseInt(document.getElementById('testSize').value);
    
    const tempSize = (valSize + testSize) / 100;
    formData.append('test_size', tempSize.toString());
    
    const valFromTemp = valSize / (valSize + testSize);
    formData.append('val_size', valFromTemp.toString());
    
    formData.append('random_state', document.getElementById('randomState').value);
    
    try {
        const response = await fetch('/split/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const contentType = response.headers.get('content-type');
        
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Respuesta del servidor (HTML):', text);
            throw new Error('El servidor devolvió un error. Verifica los logs de Render.');
        }
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            sessionId = data.session_id;
            displayResults(data);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (err) {
        console.error('Error completo:', err);
        showError('Error al procesar el archivo: ' + err.message);
        configSection.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
        processBtn.disabled = false;
    }
}

function displayResults(data) {
    document.getElementById('statOriginal').textContent = data.stats.original.toLocaleString();
    document.getElementById('statTrain').textContent = data.stats.train.toLocaleString();
    document.getElementById('statVal').textContent = data.stats.validation.toLocaleString();
    document.getElementById('statTest').textContent = data.stats.test.toLocaleString();
    
    document.getElementById('statTrainPct').textContent = data.stats.train_pct;
    document.getElementById('statValPct').textContent = data.stats.val_pct;
    document.getElementById('statTestPct').textContent = data.stats.test_pct;
    
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    error.textContent = message;
    error.classList.remove('hidden');
    setTimeout(() => {
        error.classList.add('hidden');
    }, 5000);
}

function hideAll() {
    loading.classList.add('hidden');
    error.classList.add('hidden');
    resultsSection.classList.add('hidden');
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