from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass # easy to tune configurations 
import re # basic pacage for working with text
import numpy as np
import requests, json # for prompting  

from nltk.corpus import wordnet as wn # for working with synsets (antonyms, description, synonyms etc.)
from nltk.stem import WordNetLemmatizer # for working with same-stem words
from nltk.stem import SnowballStemmer

def expand_lexical(w: str) -> Tuple[Dict[str, set], Dict[str, set]]:
    "Returns synonyms and antonyms of the world"
    syn_by_sense, ant_by_sense = {}, {}
    for s in wn.synsets(w): # looping through all meanings of the word - in synsets from nltk form/object
        print(s.lemmas())
        print("------------")
        syn_by_sense[s.name()] = {l.name().replace("_", " ").lower() for l in s.lemmas()}
        ant = set()
        for l in s.lemmas():
            ant |= {a.name().replace("_", " ").lower() for a in l.antonyms()}
        ant_by_sense[s.name()] = ant
    return syn_by_sense, ant_by_sense


syn, ant = expand_lexical('white')
print("synonyms are: ", syn)
print("antonyms are: ", ant)
