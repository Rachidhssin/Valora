"""
Training script for the Query Router classification model.

This script generates training data from the MegaTestGenerator and fine-tunes
a small transformer model (DistilBERT-tiny or custom) to predict routing paths.

Usage:
    python scripts/train_router_model.py --model distilbert --epochs 5
    python scripts/train_router_model.py --model lstm --epochs 10
    python scripts/train_router_model.py --export-onnx
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

# Check for required packages
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    from torch.optim import AdamW
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("PyTorch not installed. Run: pip install torch")

try:
    from transformers import (
        AutoTokenizer, 
        AutoModelForSequenceClassification,
        get_linear_schedule_with_warmup
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Transformers not installed. Run: pip install transformers")

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Scikit-learn not installed. Run: pip install scikit-learn")


# ==================== DATA GENERATION ====================

def generate_training_data(samples_per_category: int = 500) -> List[Dict]:
    """Generate labeled training data from MegaTestGenerator."""
    from tests.test_router_mega import MegaTestGenerator
    
    print(f"Generating training data ({samples_per_category} samples per category)...")
    generator = MegaTestGenerator()
    tests = generator.generate_all(tests_per_category=samples_per_category)
    
    # Convert to training format
    label_map = {"fast": 0, "smart": 1, "deep": 2}
    training_data = []
    
    for test in tests:
        training_data.append({
            "query": test.query,
            "label": label_map[test.expected_path],
            "label_name": test.expected_path,
            "category": test.category
        })
    
    print(f"Generated {len(training_data)} training examples")
    
    # Print distribution
    from collections import Counter
    label_dist = Counter(d["label_name"] for d in training_data)
    print(f"Label distribution: {dict(label_dist)}")
    
    return training_data


def save_training_data(data: List[Dict], filepath: str):
    """Save training data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved training data to {filepath}")


def load_training_data(filepath: str) -> List[Dict]:
    """Load training data from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== DATASET CLASS ====================

class RouterDataset(Dataset):
    """PyTorch Dataset for router classification."""
    
    def __init__(self, data: List[Dict], tokenizer, max_length: int = 64):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        encoding = self.tokenizer(
            item["query"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(item["label"], dtype=torch.long)
        }


# ==================== CUSTOM LSTM MODEL ====================

class LSTMClassifier(nn.Module):
    """Lightweight LSTM classifier for query routing."""
    
    def __init__(self, vocab_size: int = 30000, embedding_dim: int = 128, 
                 hidden_dim: int = 128, num_classes: int = 3, dropout: float = 0.3):
        super().__init__()
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            embedding_dim, 
            hidden_dim, 
            batch_first=True, 
            bidirectional=True,
            dropout=dropout if dropout > 0 else 0
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)
    
    def forward(self, input_ids, attention_mask=None):
        # Embedding
        embedded = self.embedding(input_ids)
        
        # LSTM
        lstm_out, (hidden, cell) = self.lstm(embedded)
        
        # Concatenate forward and backward hidden states
        hidden = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim=1)
        
        # Classify
        hidden = self.dropout(hidden)
        output = self.fc(hidden)
        
        return output


class LSTMTokenizer:
    """Simple tokenizer for LSTM model."""
    
    def __init__(self, vocab_size: int = 30000):
        self.vocab_size = vocab_size
        self.word2idx = {"<pad>": 0, "<unk>": 1}
        self.idx2word = {0: "<pad>", 1: "<unk>"}
        self.next_idx = 2
    
    def fit(self, texts: List[str]):
        """Build vocabulary from texts."""
        word_counts = {}
        for text in texts:
            for word in text.lower().split():
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Keep top vocab_size-2 words
        sorted_words = sorted(word_counts.items(), key=lambda x: -x[1])
        for word, _ in sorted_words[:self.vocab_size - 2]:
            if word not in self.word2idx:
                self.word2idx[word] = self.next_idx
                self.idx2word[self.next_idx] = word
                self.next_idx += 1
        
        print(f"Vocabulary size: {len(self.word2idx)}")
    
    def __call__(self, text: str, truncation: bool = True, padding: str = "max_length",
                 max_length: int = 64, return_tensors: str = None) -> Dict:
        """Tokenize text."""
        words = text.lower().split()
        
        # Convert to indices
        ids = [self.word2idx.get(w, 1) for w in words]  # 1 = <unk>
        
        # Truncate
        if truncation and len(ids) > max_length:
            ids = ids[:max_length]
        
        # Pad
        attention_mask = [1] * len(ids)
        if padding == "max_length":
            pad_len = max_length - len(ids)
            ids = ids + [0] * pad_len
            attention_mask = attention_mask + [0] * pad_len
        
        result = {
            "input_ids": ids,
            "attention_mask": attention_mask
        }
        
        if return_tensors == "pt":
            result["input_ids"] = torch.tensor([ids])
            result["attention_mask"] = torch.tensor([attention_mask])
        
        return result
    
    def save(self, filepath: str):
        """Save tokenizer vocabulary."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "word2idx": self.word2idx,
                "vocab_size": self.vocab_size
            }, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'LSTMTokenizer':
        """Load tokenizer from file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tokenizer = cls(vocab_size=data["vocab_size"])
        tokenizer.word2idx = data["word2idx"]
        tokenizer.idx2word = {int(v): k for k, v in data["word2idx"].items()}
        tokenizer.next_idx = len(tokenizer.word2idx)
        return tokenizer


# ==================== TRAINING FUNCTIONS ====================

def train_transformer(
    train_data: List[Dict],
    val_data: List[Dict],
    model_name: str = "distilbert-base-uncased",
    output_dir: str = "models/router_model",
    epochs: int = 3,
    batch_size: int = 32,
    learning_rate: float = 2e-5,
    max_length: int = 64
):
    """Train a transformer model for routing classification."""
    
    if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
        raise ImportError("PyTorch and Transformers are required")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load tokenizer and model
    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=3,
        id2label={0: "fast", 1: "smart", 2: "deep"},
        label2id={"fast": 0, "smart": 1, "deep": 2}
    )
    model.to(device)
    
    # Create datasets
    train_dataset = RouterDataset(train_data, tokenizer, max_length)
    val_dataset = RouterDataset(val_data, tokenizer, max_length)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    # Optimizer and scheduler
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=total_steps // 10,
        num_training_steps=total_steps
    )
    
    # Training loop
    best_val_acc = 0
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch in train_loader:
            optimizer.zero_grad()
            
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)
            
            outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            
            loss.backward()
            optimizer.step()
            scheduler.step()
            
            total_loss += loss.item()
            preds = outputs.logits.argmax(-1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
        
        train_acc = correct / total
        avg_loss = total_loss / len(train_loader)
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["label"].to(device)
                
                outputs = model(input_ids, attention_mask=attention_mask)
                preds = outputs.logits.argmax(-1)
                
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        val_acc = val_correct / val_total
        
        print(f"Epoch {epoch+1}/{epochs}")
        print(f"  Train Loss: {avg_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"  Val Acc: {val_acc:.4f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs(output_dir, exist_ok=True)
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            print(f"  Saved best model (val_acc: {val_acc:.4f})")
    
    # Final evaluation
    print("\n" + "="*50)
    print("Final Evaluation:")
    print(classification_report(all_labels, all_preds, target_names=["fast", "smart", "deep"]))
    
    return model, tokenizer


def train_lstm(
    train_data: List[Dict],
    val_data: List[Dict],
    output_dir: str = "models/router_lstm",
    epochs: int = 10,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    max_length: int = 32,
    embedding_dim: int = 128,
    hidden_dim: int = 128
):
    """Train a lightweight LSTM model for routing classification."""
    
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Build tokenizer
    print("Building vocabulary...")
    tokenizer = LSTMTokenizer(vocab_size=10000)
    tokenizer.fit([d["query"] for d in train_data])
    
    # Create model
    model = LSTMClassifier(
        vocab_size=len(tokenizer.word2idx),
        embedding_dim=embedding_dim,
        hidden_dim=hidden_dim,
        num_classes=3
    )
    model.to(device)
    
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Create datasets
    train_dataset = RouterDataset(train_data, tokenizer, max_length)
    val_dataset = RouterDataset(val_data, tokenizer, max_length)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    # Optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()
    
    # Training loop
    best_val_acc = 0
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch in train_loader:
            optimizer.zero_grad()
            
            input_ids = batch["input_ids"].to(device)
            labels = batch["label"].to(device)
            
            outputs = model(input_ids)
            loss = criterion(outputs, labels)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            preds = outputs.argmax(-1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
        
        train_acc = correct / total
        avg_loss = total_loss / len(train_loader)
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                labels = batch["label"].to(device)
                
                outputs = model(input_ids)
                preds = outputs.argmax(-1)
                
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        val_acc = val_correct / val_total
        
        print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}, Train: {train_acc:.4f}, Val: {val_acc:.4f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs(output_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(output_dir, "model.pt"))
            tokenizer.save(os.path.join(output_dir, "tokenizer.json"))
            
            # Save config
            config = {
                "vocab_size": len(tokenizer.word2idx),
                "embedding_dim": embedding_dim,
                "hidden_dim": hidden_dim,
                "max_length": max_length,
                "num_classes": 3,
                "id2label": {0: "fast", 1: "smart", 2: "deep"}
            }
            with open(os.path.join(output_dir, "config.json"), 'w') as f:
                json.dump(config, f)
            
            print(f"  Saved best model (val_acc: {val_acc:.4f})")
    
    # Final evaluation
    if SKLEARN_AVAILABLE:
        print("\n" + "="*50)
        print("Final Evaluation:")
        print(classification_report(all_labels, all_preds, target_names=["fast", "smart", "deep"]))
    
    return model, tokenizer


def export_to_onnx(model_dir: str, output_path: str = None, model_type: str = "transformer"):
    """Export trained model to ONNX format for faster inference."""
    
    if output_path is None:
        output_path = os.path.join(model_dir, "model.onnx")
    
    if model_type == "transformer":
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.eval()
        
        # Dummy input
        dummy_input = tokenizer("best gaming laptop", return_tensors="pt", padding="max_length", max_length=64)
        
        torch.onnx.export(
            model,
            (dummy_input["input_ids"], dummy_input["attention_mask"]),
            output_path,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size"},
                "attention_mask": {0: "batch_size"},
                "logits": {0: "batch_size"}
            },
            opset_version=14
        )
    else:
        # LSTM model
        with open(os.path.join(model_dir, "config.json")) as f:
            config = json.load(f)
        
        model = LSTMClassifier(
            vocab_size=config["vocab_size"],
            embedding_dim=config["embedding_dim"],
            hidden_dim=config["hidden_dim"],
            num_classes=config["num_classes"]
        )
        model.load_state_dict(torch.load(os.path.join(model_dir, "model.pt")))
        model.eval()
        
        dummy_input = torch.randint(0, 100, (1, config["max_length"]))
        
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            input_names=["input_ids"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "seq_length"},
                "logits": {0: "batch_size"}
            },
            opset_version=14
        )
    
    print(f"Exported ONNX model to {output_path}")
    
    # Print model size
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Model size: {size_mb:.2f} MB")


# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(description="Train router classification model")
    parser.add_argument("--model", choices=["transformer", "lstm", "distilbert"], 
                       default="lstm", help="Model type to train")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--samples", type=int, default=500, 
                       help="Samples per category for training data")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--data-file", type=str, default=None, 
                       help="Load training data from file instead of generating")
    parser.add_argument("--save-data", type=str, default=None, 
                       help="Save generated training data to file")
    parser.add_argument("--export-onnx", action="store_true", help="Export to ONNX after training")
    
    args = parser.parse_args()
    
    # Check dependencies
    if not TORCH_AVAILABLE:
        print("Error: PyTorch is required. Install with: pip install torch")
        return
    
    if args.model in ["transformer", "distilbert"] and not TRANSFORMERS_AVAILABLE:
        print("Error: Transformers is required. Install with: pip install transformers")
        return
    
    # Load or generate training data
    if args.data_file and os.path.exists(args.data_file):
        print(f"Loading training data from {args.data_file}")
        data = load_training_data(args.data_file)
    else:
        data = generate_training_data(samples_per_category=args.samples)
        
        if args.save_data:
            save_training_data(data, args.save_data)
    
    # Split data
    train_data, val_data = train_test_split(data, test_size=0.15, random_state=42,
                                            stratify=[d["label"] for d in data])
    print(f"Train: {len(train_data)}, Val: {len(val_data)}")
    
    # Set output directory
    if args.output_dir is None:
        args.output_dir = f"models/router_{args.model}"
    
    # Train model
    if args.model == "lstm":
        model, tokenizer = train_lstm(
            train_data, val_data,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size
        )
    else:
        model_name = "distilbert-base-uncased"
        if args.model == "distilbert":
            model_name = "distilbert-base-uncased"
        
        model, tokenizer = train_transformer(
            train_data, val_data,
            model_name=model_name,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size
        )
    
    # Export to ONNX
    if args.export_onnx:
        export_to_onnx(args.output_dir, model_type=args.model)
    
    print("\n" + "="*50)
    print(f"Training complete! Model saved to: {args.output_dir}")
    print("\nTo use in the hybrid router:")
    print(f'  router = HybridQueryRouter(model_path="{args.output_dir}")')


if __name__ == "__main__":
    main()
