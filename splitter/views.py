from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from sklearn.model_selection import train_test_split
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import arff
import zipfile
import os
from pathlib import Path

def index(request):
    """Render main page"""
    return render(request, 'splitter/index.html')

def load_arff_file(file_content):
    """Load ARFF file and return DataFrame"""
    dataset = arff.loads(file_content)
    attributes = [attr[0] for attr in dataset["attributes"]]
    return pd.DataFrame(dataset['data'], columns=attributes)

def create_histogram(data, column, title):
    """Create histogram for a specific column matching Jupyter style"""
    # Use default matplotlib style (like Jupyter)
    plt.style.use('default')
    
    # Create figure with white background
    fig, ax = plt.subplots(figsize=(6.4, 4.8), facecolor='white')
    ax.set_facecolor('white')
    
    # Create histogram with Jupyter-like colors
    data[column].dropna().hist(
        bins=20, 
        edgecolor='black',
        linewidth=0.5,
        color='#1f77b4',  # Matplotlib default blue
        alpha=1.0,
        ax=ax
    )
    
    # Title and labels - simple like Jupyter
    ax.set_title(title, fontsize=11)
    ax.set_xlabel(column, fontsize=10)
    ax.set_ylabel('Frequency', fontsize=10)
    
    # Simple grid like Jupyter
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Keep all spines visible (like Jupyter)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor('black')
        spine.set_linewidth(0.8)
    
    # Tick styling
    ax.tick_params(labelsize=9)
    
    # Tight layout
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

def dataframe_to_arff(df, relation_name='dataset'):
    """Convert DataFrame to ARFF format string"""
    arff_dict = {
        'relation': relation_name,
        'attributes': [],
        'data': df.values.tolist()
    }
    
    for col in df.columns:
        dtype = df[col].dtype
        if dtype == 'object' or dtype.name == 'category':
            unique_values = df[col].unique().tolist()
            arff_dict['attributes'].append((col, unique_values))
        elif dtype == 'float64' or dtype == 'float32':
            arff_dict['attributes'].append((col, 'REAL'))
        else:
            arff_dict['attributes'].append((col, 'NUMERIC'))
    
    return arff.dumps(arff_dict)

def split_dataset(request):
    """Split uploaded ARFF dataset into train/validation/test sets"""
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        if not uploaded_file.name.endswith('.arff'):
            return JsonResponse({'error': 'El archivo debe ser .arff'}, status=400)
        
        try:
            # Read and parse ARFF file
            content = uploaded_file.read().decode('utf-8')
            df = load_arff_file(content)
            
            # Get split ratios (default: 60% train, 20% val, 20% test)
            test_size = float(request.POST.get('test_size', 0.4))
            val_size = float(request.POST.get('val_size', 0.5))
            random_state = int(request.POST.get('random_state', 42))
            
            # First split: 60% train, 40% temp
            train_set, temp_set = train_test_split(
                df, 
                test_size=test_size, 
                random_state=random_state
            )
            
            # Second split: 50% validation, 50% test (from temp_set)
            val_set, test_set = train_test_split(
                temp_set, 
                test_size=val_size, 
                random_state=random_state
            )
            
            # Find a column for histogram (prefer 'protocol_type' or first categorical)
            plot_column = None
            for col in df.columns:
                if col == 'protocol_type':
                    plot_column = col
                    break
                elif df[col].dtype == 'object':
                    plot_column = col
                    break
            
            # If no categorical column found, use first numeric column
            if plot_column is None:
                plot_column = df.columns[0]
            
            # Create histograms
            plots = {
                'train': create_histogram(train_set, plot_column, f'Training Set - {plot_column}'),
                'val': create_histogram(val_set, plot_column, f'Validation Set - {plot_column}'),
                'test': create_histogram(test_set, plot_column, f'Test Set - {plot_column}'),
                'original': create_histogram(df, plot_column, f'Original Dataset - {plot_column}')
            }
            
            # Save datasets temporarily
            session_id = request.session.session_key or request.session.create()
            temp_dir = Path(f'/tmp/splits_{session_id}')
            temp_dir.mkdir(exist_ok=True)
            
            # Convert DataFrames to ARFF and save
            train_arff = dataframe_to_arff(train_set, 'train_set')
            val_arff = dataframe_to_arff(val_set, 'validation_set')
            test_arff = dataframe_to_arff(test_set, 'test_set')
            
            with open(temp_dir / 'train.arff', 'w') as f:
                f.write(train_arff)
            with open(temp_dir / 'validation.arff', 'w') as f:
                f.write(val_arff)
            with open(temp_dir / 'test.arff', 'w') as f:
                f.write(test_arff)
            
            # Prepare response
            response = {
                'success': True,
                'stats': {
                    'original': len(df),
                    'train': len(train_set),
                    'validation': len(val_set),
                    'test': len(test_set),
                    'train_pct': round(len(train_set) / len(df) * 100, 2),
                    'val_pct': round(len(val_set) / len(df) * 100, 2),
                    'test_pct': round(len(test_set) / len(df) * 100, 2)
                },
                'plots': plots,
                'session_id': session_id
            }
            
            return JsonResponse(response)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al procesar archivo: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)

def download_splits(request):
    """Download all split datasets as a ZIP file"""
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({'error': 'Session ID requerido'}, status=400)
    
    temp_dir = Path(f'/tmp/splits_{session_id}')
    if not temp_dir.exists():
        return JsonResponse({'error': 'Archivos no encontrados'}, status=404)
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in temp_dir.glob('*.arff'):
            zip_file.write(file_path, file_path.name)
    
    zip_buffer.seek(0)
    
    # Clean up temp files
    for file in temp_dir.glob('*.arff'):
        file.unlink()
    temp_dir.rmdir()
    
    response = FileResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="dataset_splits.zip"'
    
    return response
