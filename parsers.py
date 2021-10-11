from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams
import re
import streamlit as st


def get_page_types(file):
    for page in extract_pages(file):
        type = None
        if any('+Custos BM&F' in g.get_text() for g in  page.groups):
            type = 'BMF'
        else:
            type ='B3'
        yield type

@st.experimental_memo(show_spinner=False)
def parse_bmf_page(file, page_numbers, password=''):
    parsed = []
    if not page_numbers:
        return parsed
    #extrai os ativos
    params = LAParams(line_overlap=0, char_margin=10000, line_margin=0.5, word_margin=0.1, boxes_flow=0.5, detect_vertical=False, all_texts=False)
    for n, page in enumerate(extract_pages(file, password, page_numbers=page_numbers, laparams=params)):
        try:
            parsed_page = dict(arquivo=file.name, pagina=page_numbers[n], tipo='BMF')
            text = []
            for element in page:
                if hasattr(element, 'get_text'):
                    text.append(element.get_text())
            text = ''.join(text)

            parsed_page['nota']=re.findall(r"Nr. nota((?:\d+)\.*(?:\d*))",text)[0]
            parsed_page['data_pregao'] = re.findall(r"Data pregão(\d\d/\d\d/\d\d\d\d)",text)[0]
            parsed_page['folha'] = re.findall(r"Folha\s+(\d+)",text)[0]

            rex = re.compile(r"(?:C/V.*?Operacional)(.*?)(?:.C\.N\.)", re.IGNORECASE | re.DOTALL)
            text = re.search(rex, text)

            text = [l for l in text.expand(r"\1").split('\n') if  l.strip() != '']
            rex_ativo = re.compile(r"""
            (?P<CV>C|V)\s+
            (?P<Mercadoria>.*?)\s+.?
            (?P<Vencimento>\d{2}/\d{2}/\d{4})\s+
            (?P<Quantidade>\d+)\s+
            (?P<Preço_Ajuste>(?:\d+\.)*(?:\d+,)\d+)\s+
            (?P<Tipo_Negocio>.*?)\s+
            (?P<Valor_Operacao>(?:\d+\.)*(?:\d+,)\d+)\s+
            (?P<DC>D|C)\s+
            (?P<Taxa_Operacional>(?:\d+\.)*(?:\d+,)\d+)
            """, re.VERBOSE | re.IGNORECASE)

            parsed_page['operacoes'] = []
            for t in text:
                parsed_page['operacoes'].append(re.search(rex_ativo, t).groupdict())

            parsed.append(parsed_page)
        except Exception as ex:
            parsed_page = dict(page_number=page_numbers[n], type='Error')
            parsed_page['Message'] = "Erro extraindo operações B3"
            parsed_page['Text'] = text
            parsed_page['Exception'] = ex
            parsed.append(parsed_page)
            raise ex

    #extrais o resumo
    params = LAParams(line_margin=0, word_margin=0.5, char_margin=1000)
    for i, page in enumerate(extract_pages(file, password, page_numbers=page_numbers, laparams=params)):
        try:
            text = []
            for element in page:
                if hasattr(element, 'get_text'):
                    text.append(element.get_text())
            text = ''.join(text)
            custos = re.findall(r"((?:\d+\.)*(?:\d+,)\d\d)",text.split('Venda disponível')[-1]) #todos os valores de "venda disponível em diante"
            cols = ["venda_disponivel", "compra_disponivel", "venda_opcao", "compra_opcao", "valor_dos_negocios", "irrf", 
            "irrf_day_trade", "taxa_operacional", "taxa_registro_bmf", "taxa_bmf", "outos_custos", "iss", "ajuste_de_posicao", "ajuste_day_trade", 
            "total_custos_operacionais", "outos", "irrf_operacional", "total_conta_investimento", "total_conta_normal", "total_liquido", "total_liquido_da_nota"]
            data_bmf = dict(zip(cols, custos))
            parsed[i]['resumo'] = data_bmf
        
        except Exception as ex:
            parsed_page = dict(page_number=page_numbers[n], type='Error')
            parsed_page['Message'] = "Erro extraindo operações B3"
            parsed_page['Text'] = text
            parsed_page['Exception'] = ex
            parsed.append(parsed_page)
            raise 
            
    return parsed   

@st.experimental_memo(show_spinner=False)
def parse_b3_page(file, page_numbers, password=''):
    parsed = []
    if not page_numbers:
        return parsed

    #extrai os ativos
    params = LAParams(line_overlap=0, char_margin=10000, line_margin=0.5, word_margin=0.1, boxes_flow=0.5, detect_vertical=False, all_texts=False)
    for n,page in enumerate(extract_pages(file, password, page_numbers=page_numbers, laparams=params)):
        try:
            parsed_page = dict(arquivo=file.name, pagina=page_numbers[n], tipo='B3')
            text = []
            for element in page:
                if hasattr(element, 'get_text'):
                    text.append(element.get_text())
            text = ''.join(text)

            parsed_page['nota']=re.findall(r"Nr. nota((?:\d+)\.*(?:\d*))",text)[0]
            parsed_page['data_pregao'] = re.findall(r"Data pregão(\d\d/\d\d/\d\d\d\d)",text)[0]
            parsed_page['folha'] = re.findall(r"Folha\s+(\d+)",text)[0]

            rex = re.compile(r"(?:Q\s+Negocia.*?D/C)(.*?)(?:Resumo dos Ne)", re.IGNORECASE | re.DOTALL)
            
            text = re.search(rex, text)

            text = [l for l in text.expand(r"\1").split('\n') if  l.strip() != '']
            rex_ativo = re.compile(r"""
            (?P<Negociacao>(.*?))(?=\sC|\sV)\s+
            (?P<CV>(C|V))\s+
            (?P<titulo>(.*)(?=\s\d+\.?\d*\s))\s+
            (?P<quantidade>\d+\.?\d*)\s+
            (?P<preco>(?:\d+\.)*(?:\d+,)\d+)\s+
            (?P<valor_operacao>(?:\d+\.)*(?:\d+,)\d+)\s+
            (?P<DC>D|C)
            """, re.VERBOSE | re.IGNORECASE)

            parsed_page['operacoes'] = []
            for t in text:
                op_line = {}
                extraction = re.search(rex_ativo, t).groupdict()

                op_line.update(extraction)
                parsed_page['operacoes'].append(op_line)

            parsed.append(parsed_page)
        except Exception as ex:
            parsed_page = dict(page_number=page_numbers[n], type='Error')
            parsed_page['Message'] = "Erro extraindo operações B3"
            parsed_page['Text'] = text
            parsed_page['Exception'] = ex
            parsed.append(parsed_page)

    params = LAParams(line_margin=0, word_margin=0, char_margin=10000, boxes_flow=False)
    for i, page in enumerate(extract_pages(file, password, page_numbers=page_numbers, laparams=params)):
        try:
            text = []
            for element in page:
                if hasattr(element, 'get_text'):
                    text.append(element.get_text())
            text = ''.join(text)

            texto_resumo = text.split('Resumo Financeiro')[-1]
            rex = re.compile(r"""
            ((?:\d+\.)*(?:\d+,)\d+(?:\D)(?:\D|\s)+?(?=\d))
            """, re.VERBOSE)
            parsed[i]['resumo'] = {}

            #resumo dos negócios 
            rex = re.compile(r"""
            ((?:\d+\.)*(?:\d+,)\d+)(?=.*Bolsa)
            """, re.VERBOSE | re.DOTALL)
            resumo_dos_negocios = ['Debêntures', 'Vendas a Vista', 'Compras a Vista', 'Opções - Compras', 'Opções - Vendas', 'Operações à termo', 'Valor das Oper. c/ Títulos Públicos (v.nom)', 'Valor das Operações']
            resumo_dos_negocios = dict(zip(resumo_dos_negocios, re.findall(rex, texto_resumo)))
            parsed[i]['resumo'].update(resumo_dos_negocios)
            
            #Resumo Financeiro
            for item in re.findall(rex, texto_resumo):
                z = re.findall(r"((?:\d+\.)*(?:\d+,)\d+)(.*)(?:C|D)", item)
                z = {i[1]:i[0] for i in z if i}
                parsed[i]['resumo'].update(z)
        except Exception as ex:
            parsed_page = dict(pagina=page_numbers[n], tipo='Error')
            parsed_page['Message'] = "Erro extraindo operações B3"
            parsed_page['Text'] = text
            parsed_page['Exception'] = ex
            parsed.append(parsed_page)

    return parsed