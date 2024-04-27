#!/usr/bin/env python
# coding: utf-8

# In[11]:


from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter,MarkdownHeaderTextSplitter
from langchain.chains import VectorDBQA
from langchain.document_loaders import TextLoader,DirectoryLoader
from sentence_transformers import SentenceTransformer
import requests
import json
import os 
import re
import numpy as np
import faiss
import pickle
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.vectorstores.faiss import FAISS


# In[2]:


from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings,HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.llms import HuggingFaceHub
from tqdm.auto import tqdm


# In[3]:


def get_pdf_text(pdf_docs):
    texts = []
    attribute = []
    for pdf in tqdm(pdf_docs):
        text = ''
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
        texts.append(text)
    return texts
    
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=128,
        length_function=len
            )
    chunks = text_splitter.split_documents(text)
    return chunks
    


# In[4]:


#import streamlit as st
#@st.cache_data
def load_faiss_index():
    with open('chunks_gb.pickle', 'rb') as handle:
        chunks = pickle.load(handle)

    model = SentenceTransformer('BAAI/bge-m3',device="cpu")
    embeddings = np.load('embs-gb.npy')

    index = faiss.IndexFlatL2(embeddings.shape[1])   # build the index
    index.add(embeddings)     

    return chunks, model, index, embeddings

def get_relevant_documents(question, chunks, model, index, embeddings):
    k = 3 #NUM of retrieval candidates
    e = model.encode(question)
    dist, Idx = index.search(e.reshape(1,-1), k)
    retrievals = [chunks[i] for i in Idx.flatten()]
    return retrievals  


# In[28]:


def generate_mixtral_response(question, chunks, model, index, embeddings):
    rets = get_relevant_documents(question, chunks, model, index, embeddings)
    metadatas = [list(item.metadata.keys())[0] for item in rets]
    
    # Improved string formatting
    sources_text = ' \n\n '.join([f'ИСТОЧНИК {i+1}: {ret.page_content}' for i, ret in enumerate(rets)])
    
    promptstring = (
        f"Вы программист, который точно отвечает на вопросы пользователей на темы, связанные с программированием. "
        f"Используя информацию, содержащуюся в пронумерованных ИСТОЧНИКАХ после слова ТЕКСТ, "
        f"ответьте на вопрос, заданный после слова ВОПРОС. "
        f"Если в тексте нет информации, необходимой для ответа, ответьте «Недостаточно информации для ответа». "
        f"Структурируйте свой ответ и отвечайте шаг за шагом. При ответе с использованием информации из текста, "
        f"используйте ссылки в скобках, содержащие номер ИСТОЧНИКА с релевантной информацией.\n"
        f"ТЕКСТ:\n{sources_text}\nВОПРОС:\n{question}"
    )

    #print(promptstring)
    endpoint = 'https://api.together.xyz/v1/chat/completions'
    res = requests.post(endpoint, json={
    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "max_tokens": 2048,
    "prompt": f"[INST] {promptstring}  [/INST]",
    "temperature": 0.4,
    "top_p": 0.7,
    "top_k": 5,
    "repetition_penalty": 1,
    "stop": [
        "[/INST]",
        "</s>"
    ],
    "repetitive_penalty": 1,
    "update_at": "2024-02-25T16:35:32.555Z"
}, headers={
    "Authorization": "Bearer fba55128c5cf945c1c3e8349d5e86b2d284015f2faf0eab3c0cd46ab4dfef179",
})
    print(dict(json.loads(res.content))['usage']['total_tokens'])
    return dict(json.loads(res.content))['choices'][0]['message']['content'],metadatas,rets


# In[18]:


def generate_mixtral_comment(question, answer, chunks, model, index, embeddings):
    rets = get_relevant_documents(question, chunks, model, index, embeddings)
    metadatas = [list(item.metadata.keys())[0] for item in rets]
    
    # Improved string formatting
    sources_text = ' \n\n '.join([f'ИСТОЧНИК {i+1}: {ret.page_content}' for i, ret in enumerate(rets)])
    
    promptstring = (
        f"Вы программист, который точно отвечает на вопросы пользователей на темы, связанные с программированием. "
        f"Используя информацию, содержащуюся в пронумерованных ИСТОЧНИКАХ после слова ТЕКСТ, "
        f"оцените правильность высказывания, приведенного после слова ОТВЕТ, как ответ на вопрос, заданный после слова ВОПРОС. "
        f"Если в тексте нет информации, необходимой для ответа, ответьте «0*». " #Недостаточно информации для ответа
        f"Если высказывание после слова ОТВЕТ правильное, ответьте «1*». Если высказывание после слова ОТВЕТ неправильное, ответьте «0*».\n "
        f"ТЕКСТ:\n{sources_text}\nВОПРОС:\n{question}\nОТВЕТ:{answer}"
    )

    #print(promptstring)
    endpoint = 'https://api.together.xyz/v1/chat/completions'
    res = requests.post(endpoint, json={
    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "max_tokens": 2048,
    "prompt": f"[INST] {promptstring}  [/INST]",
    "temperature": 0.4,
    "top_p": 0.7,
    "top_k": 5,
    "repetition_penalty": 1,
    "stop": [
        "[/INST]",
        "</s>"
    ],
    "repetitive_penalty": 1,
    "update_at": "2024-02-25T16:35:32.555Z"
}, headers={
    "Authorization": "Bearer fba55128c5cf945c1c3e8349d5e86b2d284015f2faf0eab3c0cd46ab4dfef179",
})
    print(dict(json.loads(res.content))['usage']['total_tokens'])
    return dict(json.loads(res.content))['choices'][0]['message']['content'],metadatas,rets


# In[19]:


#prompt = ''
def respond_question(prompt):
    if prompt:
        
        # Check which model is selected and call the corresponding function
        chunks, model, index, embeddings = load_faiss_index()  
        response, metadatas, rets = generate_mixtral_comment(question, answer, chunks, model, index, embeddings)#generate_mixtral_response(prompt, chunks, model, index, embeddings)
            # Process and display the response
        excerpts = '\n\n'.join([f"ИСТОЧНИК {i + 1}, {list(ret.metadata.keys())[0]}: {ret.page_content}" for i, ret in enumerate(rets)]) if rets else ""
        bibliography = '\n\n'.join([f"{i + 1}. {meta}" for i, meta in enumerate(metadatas)]) if metadatas else ""
        full_response = f"{response}\n\nИСТОЧНИКИ:\n{excerpts}\n\nСПИСОК ЛИТЕРАТУРЫ:\n\n{bibliography}"
    return full_response#f"{response}#\n\nИСТОЧНИКИ:\n{excerpts}\n\nСПИСОК ЛИТЕРАТУРЫ:\n\n{bibliography}"#full_response
  


# In[20]:


def qa_check(question, answer):
    question = 'на ВОПРОС: ' + question + ' был дан ОТВЕТ: ' + answer + '. Если ОТВЕТ правильный, выведи число 1. Если ОТВЕТ не правильный, выведи число 0. Давай все ответы на русском языке'
    retrieval_results = list(ensemble_retriever.get_relevant_documents(question))
    text = ' \n\n '.join([re.sub(r'\W+', ' ', ret.page_content) for ret in retrieval_results])
    metadatas = list(set([list(item.metadata.keys())[0] for item in retrieval_results]))
    #metadatas
   # print(question)
    #print(simple_question_answering(question))
    return simple_question_answering(question)


# In[29]:


import pandas as pd
data = pd.read_csv('train_data.csv')
data.head()


# In[33]:


#respond_question(prompt)

for i in tqdm(range(len(data))):
    question, answer, corr = data.iloc[i, :3]
   # print(question, answer)
    reply = respond_question(question)
   # print(reply)
    tmp = reply.replace('\n','').lower()
    #print(tmp)
    start = tmp.find('ответ:')
    start = tmp.find('*', start+1)
 
    end = start
    #print('end', end)
    output = tmp[end-2:end]
    print('Правильность ответа: ', output, ' Correct answer: ', corr)
    data.loc[i, 'Model output'] = output
#clean&correct responce
data['Model output_corr'] = [int(1) if '1' in row else int(0) for row in data['Model output']]   


# In[24]:


import numpy as np
from sklearn.metrics import f1_score
y_true = data['Correctness']
y_pred = data['Model output_corr']
print(f1_score(y_true, y_pred, average='macro'))
print(f1_score(y_true, y_pred, average='micro'))
print(f1_score(y_true, y_pred, average='weighted'))
print(f1_score(y_true, y_pred, average=None))


# In[242]:


data[data['Model output']!=data['Correctness']]


# In[40]:


def check_Q_A_pair(question, answer):
    
    reply = respond_question(question)
    tmp = reply.replace('\n','').lower()
    start = tmp.find('ответ:')
    start = tmp.find('*', start+1)
    end = start
    output = tmp[end-2:end]
    result = [int(1) if '1' in output else int(0)]
    return result
    


# In[53]:


question, answer = data.iloc[11, :2]
print(question, answer)
result = check_Q_A_pair(question, answer)
print(result)


# In[54]:


print(result)


# In[27]:


# This is the part for estimation of the question-answer pair and giving the result - data1 - dataframe with test answers

data_test = pd.read_csv('test_data.csv')
#print(data_test.head())
data1 = data_test.copy()
data1['Correctness'] = 0

for i in tqdm(range(len(data1))):
    question, answer, corr = data1.iloc[i, :3]
    #print(question, answer)
    reply = respond_question(question)
    tmp = reply.replace('\n','').lower()
    start = tmp.find('ответ:')
    start = tmp.find('*', start+1)
    end = start
    output = tmp[end-2:end]
    print('Правильность ответа: ', output)
    data1.loc[i, 'Model output'] = output
data_final = data1.copy()
data_final['Model output_corr'] = [int(1) if '1' in row else int(0) for row in data_final['Model output']]

submission = pd.read_csv('sample_submission.csv')
submission.hash = 0
submission['Correctness'] = data_final['Model output_corr']
submission.to_csv('submission_gb.csv', index= False)


# In[31]:


submission = pd.read_csv('submission_gb.csv')
submission


# In[ ]:




