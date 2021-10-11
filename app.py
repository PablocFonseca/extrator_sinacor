import streamlit as st
import pandas as pd 
from parsers import * 
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Extrator Notas de Corretagem - (c) Pablo Fonseca", layout='wide')

consolidado  = defaultdict(list)

def get_consolidado(consolidado):
    io = BytesIO()
    file = pd.ExcelWriter(io, engine='auto')
    for k in consolidado:
        if consolidado[k]:
            df = pd.concat(consolidado[k])
            df.to_excel(file, sheet_name=k, index=False)
    file.save()
    io.seek(0)
    return io


col1, col2 = st.columns([3,1])
with col1:
    files = st.file_uploader("Carregar Notas no padrão SINACOR", ['pdf'], accept_multiple_files=True)

with col2:
    st.subheader(' ')
    st.subheader(' ')
    holder = st.container()

st.markdown('---')
st.text('Dados Extraídos')
for file in files:
    types = list(get_page_types(file))
    bmf_pages_indexes = [i for i,j in enumerate(types) if j == 'BMF']
    b3_pages_indexes = [i for i,j in enumerate(types) if j == 'B3']
    with st.spinner(f"Processando {file.name}"):
        b3_content = parse_b3_page(file, b3_pages_indexes)
        bmf_content = parse_bmf_page(file, bmf_pages_indexes)

    content = list(sorted(b3_content + bmf_content, key=lambda i: i['pagina']))
    
    with st.expander(f"{file.name} - {len(content)} Páginas"):
        
        op = pd.json_normalize(b3_content, 'operacoes', ['nota','pagina','tipo', 'arquivo'])
        if not op.empty:
            st.text('Operações B3:')
            consolidado['operacoes_b3'].append(op)
            st.write(op)

        
        d = {i['nota']:pd.Series(i['resumo']) for i in b3_content}
        if d:
            st.text('Resumo B3')
            resumo = pd.concat(d, axis=1).T
            resumo.index.name = 'Nota'
            consolidado['resumo_b3'].append(resumo)
            st.dataframe(resumo.reset_index())

        op = pd.json_normalize(bmf_content, 'operacoes', ['nota','pagina','tipo','arquivo'])
        if not op.empty:
            st.text('Operações BM&F:')
            consolidado['operacoes_bmf'].append(op)
            st.write(op)
        
        d = {i['nota']:pd.Series(i['resumo']) for i in bmf_content}
        if d:
            st.text('Resumo BM&F')
            resumo = pd.concat(d, axis=1).T
            resumo.index.name = 'Nota'
            consolidado['resumo_bmf'].append(resumo)
            st.dataframe(resumo.reset_index())

if files:
    data = get_consolidado(consolidado)
    holder.download_button(label="Baixar Arquivo Consolidado", data=data, file_name="consolidado.xlsx", mime='application/vnd.ms-excel')
else:
    holder.markdown("<button kind='primary' class='css-160hik1 edgvbvh1' disabled>Baixar Arquivo Consolidado</button>", unsafe_allow_html=True)

          