import time
print("Starting example training...")
for epoch in range(1, 6):
    print(f"Epoch {epoch}/5: training...")
    time.sleep(1)
    print(f"Epoch {epoch}: loss={(6-epoch)/5:.3f}, acc={epoch/5:.3f}")
print("Training complete!")
