import random

class WordLoader:
    # for now something that mocks
    def __init__(self):
        # usuallly it initializes the WordSampler, embeddings, creates forbidden API and build vocabulary
        # self.idx = EmbedIndex()
        # self.api = ForbiddenAPI()
        self.vocabulary = ["banana"]
    
    def generate_target_word(self):
        return random.choices(self.vocabulary)
    
    def check_describtion(self): # for now all good
        return True
    
    def generate_forbidden_list(self, word):
        return ["fruit", "kaka", "banan"]