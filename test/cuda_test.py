# https://github.com/pytorch/pytorch/issues/17108
# cuda version and so on
import torch
print("torch.cuda.is_available()   =", torch.cuda.is_available())
print("torch.cuda.device_count()   =", torch.cuda.device_count())
print("torch.cuda.device('cuda')   =", torch.cuda.device('cuda'))
print("torch.cuda.current_device() =", torch.cuda.current_device())
print("torch.version.cuda =", torch.version.cuda)