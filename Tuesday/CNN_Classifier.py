from __future__ import print_function, division
import os
import scipy.ndimage
import torch
import random
import matplotlib.pyplot as plt
import numpy as np
from torch.utils.data import DataLoader
from torchvision import transforms, utils
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
# different type of galaxies
classes = ['spiral', 'elliptical', 'uncertain']
def get_class(one_hot_vec):
    global classes
    for i in range(len(one_hot_vec)):
        if one_hot_vec[i] == 1:
            return classes[i]

# torch.backends.cudnn.enabled = False

# read in array with information
# hnd = open("./GalaxyZoo/training_data_2.txt","r")
# hnd = open("./GalaxyZoo/training_data.txt","r")
hnd = open("./Tuesday/GalaxyZoo/training_data.txt","r")
all_data = eval(hnd.read())
random.shuffle(all_data)
hnd.close()

# look at a few images
# counter = 0
# for entry in all_data:
#     image = plt.imread(os.path.join('./GalaxyZoo/', entry[0] + '.jpg'))
#     plt.figure()
#     plt.title(get_class(entry[1:]))
#     plt.imshow(image)
#     plt.show()
#     plt.imshow(scipy.ndimage.rotate(image, 90))
#     plt.show()

#     counter += 1
#     if counter == 3:
#         break

mean = 0.5
std = 0.5
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((mean, mean, mean), (std, std, std))
])

untransform = transforms.Compose([
    transforms.Normalize((-mean / std, -mean / std, -mean / std), (1.0 / std, 1.0 / std, 1.0 / std)),
    transforms.ToPILImage()
])

# detect CUDA
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("Using device", device)

# perform train:test split
max_num = 5000
max_num = min(max_num, len(all_data))
split_point = int(np.floor(0.9*max_num))

train_set, test_set = [], []
for i in range(len(all_data)):
    if i == max_num:
        break
    name, galaxy_class = all_data[i][0], all_data[i][1:]
    # image = plt.imread(os.path.join('./GalaxyZoo/', name + '.jpg'))
    image = plt.imread(os.path.join('./Tuesday/GalaxyZoo/', name + '.jpg'))
    # perform over-/ undersampling to create a balanced train set
    images = [image]
    if galaxy_class[0] == 1 and random.random() > 0.5:
        images += [scipy.ndimage.rotate(image, 180)]
    elif galaxy_class[1] == 1:
        images += [scipy.ndimage.rotate(image, 90), scipy.ndimage.rotate(image, 180), scipy.ndimage.rotate(image, 270)]
    elif galaxy_class[2] == 1 and random.random() > 0.7:
        continue

    if i <= split_point:
        for img in images:
            train_set.append([transform(np.array(img)).to(device), torch.tensor(galaxy_class).to(device)])
    else:
        for img in images:
            test_set.append([transform(img).to(device), torch.tensor(galaxy_class).to(device)])

print("(# train, # test): (" + str(len(train_set)) + ", " + str(len(test_set)) + ")\n")

# look at distribution of three classes in train set
distro = np.array([0 for _ in range(len(classes))])
for e in train_set:
    # distro = np.add(distro, e[1].numpy())
    distro = np.add(distro, e[1].cpu().numpy())

for i in range(len(classes)):
    print("{:12s}: {:1.2f}".format(classes[i], distro[i]/float(len(train_set))))


# define the NN
def get_conv_out_dim(size, padding, dilation, kernel, stride):
    return int(np.floor((size+2*padding-dilation*(kernel-1)-1)/stride + 1))


w0 = 120
w1 = get_conv_out_dim(w0, 0, 1, 8, 2)
w2 = get_conv_out_dim(w1, 0, 1, 2, 2)
w3 = get_conv_out_dim(w2, 0, 1, 8, 2)
w4 = get_conv_out_dim(w3, 0, 1, 2, 2)

class Classifyer_CNN(nn.Module):
    def __init__(self):
        super(Classifyer_CNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 6, 8, (2, 2))  # in_channels, out_channels, kernel_size, stride, padding, dilation, transposed, output_padding, groups, bias, padding_mode
        self.pool1 = nn.MaxPool2d(2, 2)  # kernel_size, stride=kernel_size, padding=0, dilation=1, return_indices=False, ceil_mode=False
        self.conv2 = nn.Conv2d(6, 16, 8, (2, 2))
        self.pool2 = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(16 * w4 * w4, 120)
        self.fc2 = nn.Linear(120, 60)
        self.fc3 = nn.Linear(60, 3)

    def forward(self, x):
        x=x.cuda()
        x = F.relu(self.conv1(x))
        x = self.pool1(x)
        x = F.relu(self.conv2(x))
        x = self.pool2(x)
        x = x.view(-1, 16 * w4 * w4)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        # x = F.softmax(self.fc3(x), dim=1)
        x = self.fc3(x)  # DON'T take softmax, this is done automatically in the loss criterion
        return x


net = Classifyer_CNN()
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)

net.to(device)

trainloader = DataLoader(dataset=train_set, batch_size=1, shuffle=True)
testloader = DataLoader(dataset=test_set, batch_size=1, shuffle=False)
num_epochs = 50 #10
for epoch in range(num_epochs):  # loop over the dataset multiple times
    running_loss = 0.0
    print("##################################################################################")
    print("Epoch", epoch)
    for i, data in enumerate(trainloader, 0):

        inputs, labels = data
        inputs, labels = Variable(inputs.to(device)), Variable(labels.to(device))

        # zero the parameter gradients, note we do this after each input (SGD)
        optimizer.zero_grad()

        # forward, backward, optimize
        outputs = net(inputs).cuda()
        loss = criterion(outputs, torch.max(labels, 1)[1])
        loss.backward()
        optimizer.step()

        # print statistics
        running_loss += loss.item()
        if i % 1000 == 999:    # print every 1000
            print('Loss after {:5d} mini-batches: {:1.6f}'.format(i + 1, running_loss / 2000.))
            running_loss = 0.0

    with torch.no_grad():
        num_correct = [0, 0, 0]
        num_in_category = [0, 0, 0]
        incorrect_classified = []
        for _, data in enumerate(testloader, 0):
            inputs, labels = data
            labels = torch.max(labels, 1)[1]
            outputs = net(inputs)
            outputs = torch.max(outputs, 1)[1]
            num_in_category[labels] += 1
            if labels == outputs:
                num_correct[outputs] += 1
            else:
                incorrect_classified.append([inputs[0], classes[labels], classes[outputs]])

        for i in range(len(num_correct)):
            print("{:12s}: {:1.4f}".format(classes[i], float(num_correct[i])/float(num_in_category[i])))

        # print("{:12s}: {:5d}/{:5d} = {:1.4f}".format("Total", len(train_set)-len(incorrect_classified), len(train_set), float(len(train_set)-len(incorrect_classified)) / float(len(train_set))))
        print("{:12s}: {:5d}/{:5d} = {:1.4f}".format("Total", len(test_set)-len(incorrect_classified), len(test_set), float(len(test_set)-len(incorrect_classified)) / float(len(test_set))))
        random.shuffle(incorrect_classified)
        # for i in range(min(3, len(incorrect_classified))):
        #     plt.figure()
        #     plt.title("Label: " + incorrect_classified[i][1] + ", NN: " + incorrect_classified[i][2])
        #     plt.imshow(untransform(incorrect_classified[i][0].cpu()).convert("RGB"))
        #     plt.show()

    # with torch.no_grad():
    #     num_incorrect = [0, 0, 0]
    #     num_in_category = [0, 0, 0]
    #     correct_classified = []
    #     correct_num = 0
    #     total_num =0
    #     for _, data in enumerate(testloader, 0):
    #         inputs, labels = data
    #         labels = torch.max(labels, 1)[1]
    #         outputs = net(inputs)
    #         outputs = torch.max(outputs, 1)[1]
    #         num_in_category[labels] += 1
    #         total_num +=1
    #         if labels != outputs:
    #             num_incorrect[outputs] += 1
    #         else:
    #             correct_classified.append([inputs[0], classes[labels], classes[outputs]])
    #             correct_num +=1

    #     for i in range(len(num_incorrect)):
    #         print("{:12s}: {:1.4f}".format(classes[i], float(num_incorrect[i])/float(num_in_category[i])))

    #     # print("{:12s}: {:5d}/{:5d} = {:1.4f}".format("Total", len(train_set)-len(correct_classified), len(train_set), float(len(train_set)-len(correct_classified)) / float(len(train_set))))
    #     print("{:12s}: {:5d}/{:5d} = {:1.4f}".format("Total", int(total_num)-len(correct_classified), int(total_num), (float(total_num)-len(correct_classified)) / float(total_num) ))
    #     print(len(correct_classified))
    #     print(len(train_set))
    #     print(num_incorrect)
    #     print(correct_num)
    #     random.shuffle(correct_classified)
    #     for i in range(min(3, len(correct_classified))):
    #         plt.figure()
    #         plt.title("Label: " + correct_classified[i][1] + ", NN: " + correct_classified[i][2])
    #         plt.imshow(untransform(correct_classified[i][0].cpu()).convert("RGB"))
    #         plt.show()
       

print('Finished Training')