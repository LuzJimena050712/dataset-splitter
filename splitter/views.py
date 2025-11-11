from django.shortcuts import render
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from sklearn.model_selection import train_test_split
import pandas as pd
import arff
import zipfile
import tempfile
import os
import uuid
import traceback

def index(request):
    return render(request, 'splitter/index.html')

def load_arff_file(file_bytes):
    if isinstance(file_bytes, bytes):
        text = file_bytes.decode('utf-8', errors='replace')
    else:
        text = str(file_bytes)
    arff_obj = arff.loads(text)
    relation = arff_obj.get('relation', 'dataset')
    attributes = arff_obj.get('attributes', [])
    data = arff_obj.get('data', [])
    col_names = [attr[0] for attr in attributes]
    df = pd.DataFrame(data, columns=col_names)
    for col, attr in zip(col_names, attributes):
        typ = attr[1]
        if isinstance(typ, str):
            t = typ.upper()
            if t in ('REAL', 'NUMERIC', 'INTEGER'):
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df, relation

def dataframe_to_arff_bytes(df, relation_name='dataset'):
    attributes = []
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            attributes.append((col, 'REAL'))
        else:
            uniques = series.dropna().unique().tolist()
            uniques = [str(u) for u in uniques]
            attributes.append((col, uniques if len(uniques) > 0 else 'STRING'))
    data = df.where(pd.notnull(df), None).values.tolist()
    arff_dict = {'relation': relation_name, 'attributes': attributes, 'data': data}
    text = arff.dumps(arff_dict)
    return text.encode('utf-8')

@csrf_exempt
def split_dataset(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'ok': False, 'error': 'No file uploaded'}, status=400)
    try:
        content = file.read()
        df, relation = load_arff_file(content)
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': 'Error reading ARFF: ' + str(e)}, status=400)
    try:
        train_frac = 0.6
        val_frac = 0.2
        test_frac = 0.2
        train_df, temp_df = train_test_split(df, train_size=train_frac, random_state=int(request.POST.get('random_state', 42)), shuffle=True)
        val_relative = val_frac / (val_frac + test_frac)
        val_df, test_df = train_test_split(temp_df, train_size=val_relative, random_state=int(request.POST.get('random_state', 42)), shuffle=True)
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': 'Error splitting dataset: ' + str(e)}, status=500)
    tmp_dir = tempfile.gettempdir()
    uid = uuid.uuid4().hex
    zip_filename = f"dataset_splits_{uid}.zip"
    zip_path = os.path.join(tmp_dir, zip_filename)
    try:
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{relation}_train.arff", dataframe_to_arff_bytes(train_df, relation_name=f"{relation}_train"))
            zf.writestr(f"{relation}_validation.arff", dataframe_to_arff_bytes(val_df, relation_name=f"{relation}_validation"))
            zf.writestr(f"{relation}_test.arff", dataframe_to_arff_bytes(test_df, relation_name=f"{relation}_test"))
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': 'Error creating zip: ' + str(e)}, status=500)
    request.session['last_zip_path'] = zip_path
    stats = {'train_count': len(train_df), 'val_count': len(val_df), 'test_count': len(test_df), 'total': len(df)}
    return JsonResponse({'ok': True, 'stats': stats})

@csrf_exempt
def download_splits(request):
    zip_path = request.session.get('last_zip_path')
    if not zip_path or not os.path.exists(zip_path):
        return JsonResponse({'ok': False, 'error': 'No file available. Run split first.'}, status=400)
    response = FileResponse(open(zip_path, 'rb'), as_attachment=True, filename=os.path.basename(zip_path))
    try:
        del request.session['last_zip_path']
    except Exception:
        pass
    try:
        os.remove(zip_path)
    except Exception:
        pass
    return response

