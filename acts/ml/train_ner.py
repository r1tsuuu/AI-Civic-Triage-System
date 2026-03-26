"""
Fine-tune a spaCy NER model on Lipa City barangay examples.

Usage (from acts/):
    python ml/train_ner.py

Output:
    ml/models/ner_model_v1/   — spaCy model directory on disk
"""
import os
import random
import spacy
import spacy.cli
from spacy.training import Example

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models", "ner_model_v1")

# ---------------------------------------------------------------------------
# Training data: (text, {entities: [(start, end, label)]})
# ---------------------------------------------------------------------------
TRAIN_DATA = [
    ("Naiipit kami sa baha dito sa Sabang",
     {"entities": [(29, 35, "LOC")]}),
    ("May sunog sa Marawoy malapit sa palengke",
     {"entities": [(13, 20, "LOC")]}),
    ("Stranded ang mga tao sa Inosluban",
     {"entities": [(24, 33, "LOC")]}),
    ("Rescue please sa Mataas na Lupa, lampas tao na ang baha",
     {"entities": [(17, 31, "LOC")]}),
    ("Tulay sa Plaridel ay sira na",
     {"entities": [(9, 17, "LOC")]}),
    ("Bagsak ang poste sa Banaybanay",
     {"entities": [(20, 30, "LOC")]}),
    ("Tulong po, baha sa Lumbang!",
     {"entities": [(19, 26, "LOC")]}),
    ("Walang tubig sa Dagatan simula kahapon",
     {"entities": [(16, 23, "LOC")]}),
    ("Traffic sa Tambois dahil sa nabuwal na puno",
     {"entities": [(11, 18, "LOC")]}),
    ("May aksidente sa Pinagtongulan, kailangan ng ambulansya",
     {"entities": [(17, 30, "LOC")]}),
    ("Nakawan sa Sabang kagabi",
     {"entities": [(11, 17, "LOC")]}),
    ("Nawalan ng kuryente ang Marawoy",
     {"entities": [(24, 31, "LOC")]}),
    ("Sira ang kalsada sa Plaridel patungong Banaybanay",
     {"entities": [(20, 28, "LOC"), (39, 49, "LOC")]}),
    ("SOS mula sa Inosluban, naiipit sa baha",
     {"entities": [(12, 21, "LOC")]}),
    ("Mangagawa na ng paraan ang CDRRMO para sa Lumbang",
     {"entities": [(42, 49, "LOC")]}),
]


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Load or download base model
    print("Loading base model: xx_ent_wiki_sm")
    try:
        nlp = spacy.load("xx_ent_wiki_sm")
    except OSError:
        print("Downloading xx_ent_wiki_sm...")
        spacy.cli.download("xx_ent_wiki_sm")
        nlp = spacy.load("xx_ent_wiki_sm")

    # Ensure NER pipe exists
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")

    # Register custom labels
    for _, annotations in TRAIN_DATA:
        for ent in annotations["entities"]:
            ner.add_label(ent[2])

    # Build Example objects
    examples = []
    for text, annotations in TRAIN_DATA:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        examples.append(example)

    # Fine-tune — freeze everything except NER
    other_pipes = [p for p in nlp.pipe_names if p != "ner"]
    n_iter = 20

    print(f"Training NER for {n_iter} iterations on {len(examples)} examples...")
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.resume_training()
        for i in range(n_iter):
            random.shuffle(examples)
            losses = {}
            nlp.update(examples, sgd=optimizer, drop=0.3, losses=losses)
            if (i + 1) % 5 == 0:
                print(f"  Iteration {i + 1:2d} — NER loss: {losses.get('ner', 0):.4f}")

    print(f"Saving fine-tuned model to {MODEL_DIR} ...")
    nlp.to_disk(MODEL_DIR)
    print("Done.")


if __name__ == "__main__":
    main()
