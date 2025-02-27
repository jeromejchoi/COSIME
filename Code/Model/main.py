import argparse
import torch
import logging
import time
import os
import pandas as pd

from data_loader import load_and_prepare_data
from models import Model
from train import train_model_binary, train_model_continuous

def parse_args():
    parser = argparse.ArgumentParser(description="Train a multi-modal model.")
    parser.add_argument('--input_data_1', dest='data1_path', type=str, required=True, help="Path to the first data modality.")
    parser.add_argument('--input_data_2', dest='data2_path', type=str, required=True, help="Path to the second data modality.")
    parser.add_argument('--type', dest='m_type', type=str, choices=['binary', 'continuous'], required=True, help="Task type: binary or continuous.")
    parser.add_argument('--predictor', dest='predictor_type', type=str, choices=['regression', 'NN'], required=True, help="Predictor type: regression or neural network.")
    parser.add_argument('--fusion', type=str, choices=['early', 'late'], required=True, help="Fusion type: early or late.")
    parser.add_argument('--batch_size', type=int, default=32, help="Batch size.")
    parser.add_argument('--learning_rate', type=float, default=0.0001, help="Learning rate.")
    parser.add_argument('--learning_gamma', type=float, default=0.99, help="Learning gamma.")
    parser.add_argument('--dropout', type=float, default=0.5, help="Dropout rate.")
    parser.add_argument('--kld_1_weight', type=float, default=0.02, help="KLD weight.")
    parser.add_argument('--kld_2_weight', type=float, default=0.02, help="KLD weight.")
    parser.add_argument('--ot_weight', type=float, default=0.02, help="OT weight.")
    parser.add_argument('--cl_weight', type=float, default=0.9, help="CL weight.")
    parser.add_argument('--dim', type=int, default=100, help="Dimensionality of the embeddings.")
    parser.add_argument('--earlystop_patience', type=int, default=40, help="Early stop patience in training.")
    parser.add_argument('--delta', type=float, default=0.001, help="Minimum improvement required to reset early stopping counter.")
    parser.add_argument('--decay', type=float, default=0.001, help="Decrease in learning rate during training.")
    parser.add_argument('--epochs', type=int, default=100, help="Number of training epochs.")
    parser.add_argument('--splits', type=int, default=5, help="Number of cross-validation splits.")
    parser.add_argument('--save', dest='save_path', type=str, required=True, help="Path to save the model.")
    parser.add_argument('--log', dest='log_path', type=str, required=True, help="Path to the log file.")
    parser.add_argument('--device', type=str, default='cuda', choices=['cpu', 'cuda'], help="Device to run the model on.")
    return parser.parse_args()

def setup_logging(log_file):
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        filemode='w'
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_results(model, history, holdout_history, best_predicted_values, best_actual_values, save_path):
    torch.save(model.state_dict(), f'{save_path}/best_model.pt')
    logging.info(f"Model saved to {save_path}/best_model.pt")

    history_df = pd.DataFrame(history)
    holdout_history_df = pd.DataFrame(holdout_history)
    history_df.to_csv(f'{save_path}/history.csv', index=False)
    holdout_history_df.to_csv(f'{save_path}/holdout_history.csv', index=False)

    logging.info(f"History saved to {save_path}/history.csv")
    logging.info(f"Holdout history saved to {save_path}/holdout_history.csv")

    best_predicted_df = pd.DataFrame(best_predicted_values)
    best_actual_df = pd.DataFrame(best_actual_values)

    best_predicted_df.to_csv(f'{save_path}/best_predicted_values.csv', index=False)
    best_actual_df.to_csv(f'{save_path}/best_actual_values.csv', index=False)

    logging.info(f"Best predicted values saved to {save_path}/best_predicted_values.csv")
    logging.info(f"Best actual values saved to {save_path}/best_actual_values.csv")

def main():
    kwargs = vars(parse_args())

    # Set up logging
    setup_logging(kwargs['log_path'])
    logging.info("Starting training process...")
    start_time = time.time()

    # Load data (with None for output and name as they are not required in your case)
    train_loader_A, val_loader_A, holdout_loader_A, train_loader_B, val_loader_B, holdout_loader_B = load_and_prepare_data(
        output=None,  # Pass None if 'output' is not required
        name=None,     # Pass None if 'name' is not required
        **kwargs,
    )
    logging.info(f"Data loaded successfully from {kwargs['data1_path']} and {kwargs['data2_path']}.")

    # Get input dimensions
    sample_A = next(iter(train_loader_A))
    sample_B = next(iter(train_loader_B))
    input_dim_A = sample_A[0].shape[1]
    input_dim_B = sample_B[0].shape[1]
    logging.info(f"Input dimensions - A: {input_dim_A}, B: {input_dim_B}")

    # Initialize model
    model = Model(
        input_dim_A, input_dim_B,
        **kwargs  # Passing the remaining args
    )
    logging.info("Model initialized successfully.")

    # Train the model
    if kwargs['m_type'] == 'binary':
        model, history, holdout_history, best_predicted_values, best_actual_values = train_model_binary(model, **kwargs)
    elif kwargs['m_type'] == 'continuous':
        model, history, holdout_history, best_predicted_values, best_actual_values = train_model_continuous(model, **kwargs)
    else: raise ValueError(f'Model type {kwargs["m_type"]} not recognized')

    # Calculate training time
    training_time = time.time() - start_time
    logging.info(f"Training completed in {training_time:.2f} seconds.")

    # Save results
    create_directory(kwargs['save_path'])
    save_results(model, history, holdout_history, best_predicted_values, best_actual_values, kwargs['save_path'])

if __name__ == '__main__':
    main()
