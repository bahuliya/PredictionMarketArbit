import pickle
import time
from pathlib import Path
from sentence_transformers import SentenceTransformer
from transformers import BitsAndBytesConfig
import torch
import numpy as np


class EmbeddingConversion:
    def __init__(self, model_name, batch_size, save_interval):
        """
        Current Model - "Qwen/Qwen3-Embedding-4B"
        """
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading embedding model: {model_name} on {device}")

        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        self.model = SentenceTransformer(
            model_name,
            device=device,
            model_kwargs={"quantization_config": quantization_config}
        )

        param = next(self.model._first_module().parameters())
        print("param dtype:", param.dtype)
        print("param device:", param.device)

        self.batch_size = batch_size
        self.save_interval = save_interval
        self.save_path = Path.cwd() / 'data' / 'embeddings.pkl'
        
        # Storage
        self.all_markets = {}  
        self.all_embeddings = {}
        self.seen_ids = set()
        self.deleted_ids = {}  
        
        # Stats
        self.total_processed = 0
        self.last_save_count = 0
        self.threshold = 0


    def add_markets(self, market_infos):
        '''
        Add multiple markets - embed as batch for efficiency
        
        Args:
            market_infos: List of market_info tuples
        '''
        if not market_infos:
            return
        
        new_markets = []
        for market_info in market_infos:
            id = market_info[0]
            if id not in self.seen_ids:
                self.seen_ids.add(id)
                new_markets.append(market_info)
        
        if not new_markets:
            return
        
        # Batch embed
        descriptors = [m[2] for m in new_markets]
        embeddings = self.model.encode(
            descriptors, 
            batch_size=self.batch_size, 
            show_progress_bar=True,
            convert_to_numpy=True
        )
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        # Store everything
        for i, market_info in enumerate(new_markets):
            id = market_info[0]
            self.all_markets[id] = market_info[1:]
            self.all_embeddings[id] = embeddings[i]
            self.total_processed += 1
        
        self.save_embeddings()
            
    def save_embeddings(self):
        """Save current embeddings to disk"""
        
        # Make sure directory exists
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dict values to numpy array for efficiency
        embeddings_array = np.array(list(self.all_embeddings.values()))
        
        data = {
            'embeddings': embeddings_array,
            'markets': self.all_markets,
            'total_processed': self.total_processed,
            'timestamp': time.time()
        }
        
        with open(self.save_path, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"Saved {self.total_processed} embeddings to {self.save_path}")
        
    def get_stats(self):
        """Get current statistics"""
        return {
            'total_processed': self.total_processed,
            'total_markets': len(self.all_markets),
            'markets_since_save': self.total_processed - self.last_save_count
        }

    def delete_markets(self, tickers):
        """Delete markets by ticker/id"""
        if not tickers:
            return
        
        del_count = 0
        
        for ticker in tickers:
            if ticker not in self.deleted_ids:
                self.deleted_ids[ticker] = 2
            else:
                print("PROBLEM: Duplicate Deletion Skipped")
        
        for ticker in self.deleted_ids.copy():
            if ticker in self.all_markets:
                del self.all_markets[ticker]
                self.deleted_ids[ticker] -= 1
            if ticker in self.all_embeddings:
                del self.all_embeddings[ticker]
                self.deleted_ids[ticker] -= 1

            if self.deleted_ids[ticker] == 0:
                del self.deleted_ids[ticker]
                self.seen_ids.discard(ticker)
                del_count += 1

        if del_count > 0:
            print(f"Deleted {del_count} markets")