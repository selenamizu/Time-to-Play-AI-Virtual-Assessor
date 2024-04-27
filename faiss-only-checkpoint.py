#!/usr/bin/env python
# coding: utf-8

# In[1]:


from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings,HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter,MarkdownHeaderTextSplitter
from langchain.document_loaders import TextLoader,DirectoryLoader

import requests
import json
import os 
import re

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.vectorstores.faiss import FAISS


# In[4]:


from pypdf import PdfReader
from tqdm.auto import tqdm
import pickle
import numpy as np


# In[13]:


#search for pdf docs/materials

pdf_docs = [os.path.join('data/',f) for f in os.listdir('./data/') if '.pdf' in (f.lower())]
#pdf_docs = [os.path.join('pdfs',f) for i,f in os.listdir('./pdfs/') if '.pdf' in (f.lower())]
pdf_docs


# In[14]:


#Extracting text from pdf


import concurrent.futures
from tqdm import tqdm
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    text = ''
    pdf_reader = PdfReader(pdf_path)
    for page in pdf_reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text,pdf_path

def get_pdf_text(pdf_docs, max_workers=16):
    texts = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Map the executor to the function and the list of documents
        future_to_pdf = {executor.submit(extract_text_from_pdf, pdf): pdf for pdf in pdf_docs}
        for future in tqdm(concurrent.futures.as_completed(future_to_pdf), total=len(pdf_docs)):
            try:
                texts.append(future.result())
            except Exception as e:
                print(f"An exception occurred during PDF processing: {e}")
                pass
    return texts

# Example usage


# In[17]:


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
    


# In[18]:


#extract raw text from files
raw_text = get_pdf_text(pdf_docs)


# In[30]:


#split text into chunks 
metadatas = [{os.path.join('data/',f):i} for i,f in enumerate(os.listdir('./data/')) if '.pdf' in (f.lower())]
len(metadatas)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=256,
    chunk_overlap=128,
    length_function=len,
    is_separator_regex=True,
)

documents = text_splitter.create_documents(
    raw_text, metadatas=metadatas
)
s = text_splitter.split_documents(documents)


# In[47]:


l = [len(d.page_content) for d in s]
#max(l)
len(s)


# In[41]:


#save the database of chunks
with open('chunks_gb.pickle', 'wb') as handle:
    pickle.dump(s, handle, protocol=pickle.HIGHEST_PROTOCOL)


# In[42]:


from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-m3')


# In[43]:


chunks_text = [t.page_content for t in s]


# In[44]:


embeddings = model.encode(chunks_text,show_progress_bar = True,batch_size = 4)


# In[46]:


#save the database of chunks and embeddings
np.save("embs-gb",embeddings)

