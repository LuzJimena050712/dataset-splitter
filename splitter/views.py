from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from sklearn.model_selection import train_test_split
import pandas as pd
import io
import arff
import zipfile
from pathlib import Path

def index(request):
    """Render main page"""
    return render(request, 'splitter/index.html')

def load_arff_file(file_content):
    """Load ARFF file and return DataFrame"""
    dataset = arff.loads(file_content)
    attributes = [attr[0] for attr in dataset["attributes"]]
    return pd.DataFrame(dataset['data'], columns=attributes)

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
            arff_dict['attributes'].append