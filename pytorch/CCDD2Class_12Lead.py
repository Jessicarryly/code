import torch
import math
import numpy as np
import scipy.io as sci
import torch.nn as nn
import os
import torch.nn.functional as F
from torch.autograd import Variable
import torch.utils.data as Data
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

#torch.cuda.set_device(1)
use_cuda = torch.cuda.is_available()

N, T ,D ,L= 200, 10, 200 ,12	#batch_size, seq_length , word_dim	,leads

###############################################################################
class TrainDataset(Data.Dataset):
    def __init__(self):
        self.data_files = os.listdir('/home/lu/code/pytorch/data_dir/Train')
        #self.train_label = np.loadtxt(open('/home/lu/code/pytorch/data_dir/train_label.csv','rb'))   

    def __getitem__(self, idx):
        
        data_ori = np.loadtxt(open('/home/lu/code/pytorch/data_dir/Train/'+self.data_files[idx],'rb'),delimiter=",")   
        #num = int(self.data_files[idx].split('.')[0])
        #label = self.train_label[num-1]
        data = data_ori[0:24000]
        label = data_ori[24000]
        return data, label

    def __len__(self):
        return len(self.data_files)

trainset = TrainDataset()

train_loader = Data.DataLoader(trainset, batch_size = N,shuffle = True)

################################################################################
class TestDataset(Data.Dataset):
    def __init__(self):
        self.data_files = os.listdir('/home/lu/code/pytorch/data_dir/Test')
        #self.test_label = np.loadtxt(open('/home/lu/code/pytorch/data_dir/test_label.csv','rb'))   

    def __getitem__(self, idx):
        
        data_ori = np.loadtxt(open('/home/lu/code/pytorch/data_dir/Test/'+self.data_files[idx],'rb'),delimiter=",")   
        #num = int(self.data_files[idx].split('.')[0])
        #label = self.test_label[num-1]
        data = data_ori[0:24000]
        label = data_ori[24000]
        
        return data, label

    def __len__(self):
        return len(self.data_files)

testset = TestDataset()

test_loader = Data.DataLoader(testset, batch_size = 1, shuffle = True)

##################################################
class EncoderRNN(nn.Module):
    def __init__(self, input_size, hidden_size, n_layers=1):
        super(EncoderRNN, self).__init__()
        self.n_layers = n_layers
        self.hidden_size = hidden_size

        self.gru = nn.GRU(input_size, hidden_size, dropout = 0.5, bidirectional = True)

    def forward(self, input):
        
        output, hidden = self.gru(input)

        output = output.transpose(0,1)  ##
        
        hidden = torch.cat((hidden[0],hidden[1]),1)

        return output, hidden

class AttnDecoderRNN(nn.Module):
    def __init__(self, hidden_size, output_size, n_layers=1, dropout_p=0.001, max_length=T):
        super(AttnDecoderRNN, self).__init__()
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.n_layers = n_layers
        self.dropout_p = dropout_p
        self.max_length = max_length

        self.attn = nn.Linear(self.hidden_size*2, self.max_length)
        self.attn_combine = nn.Linear(self.hidden_size*2, self.hidden_size)
        self.dropout = nn.Dropout(self.dropout_p)
        #self.gru = nn.GRU(self.hidden_size, self.hidden_size)
        self.out = nn.Linear(self.hidden_size, self.output_size)

    def forward(self, hidden, encoder_outputs):
        attn_weights = self.attn(hidden)
        attn_applied = torch.bmm(attn_weights.unsqueeze(1), encoder_outputs)
        attn_applied = F.softmax(self.attn(attn_applied.squeeze(1)))
        attn_applied = torch.bmm(attn_applied.unsqueeze(1), encoder_outputs)
        attn_applied = attn_applied.squeeze(1)
        #output = torch.cat((input[0], attn_applied[0]), 1)
        output = self.attn_combine(attn_applied)
        output = F.tanh(output)
        output = self.out(output)
        #output = F.log_softmax(self.out(output[0]))
        
        return output, hidden, attn_weights

class LinearClass(nn.Module):
    def __init__(self, hidden_size, output_size, n_layers=1, dropout_p=0.001, max_length=L):
        super(LinearClass, self).__init__()
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.n_layers = n_layers
        self.dropout_p = dropout_p
        self.max_length = max_length

        self.attn = nn.Linear(4800, self.max_length)
        self.attn2 = nn.Linear(self.hidden_size, self.max_length)
        self.attn_combine = nn.Linear(self.hidden_size, self.hidden_size)
        self.dropout = nn.Dropout(self.dropout_p)
        #self.gru = nn.GRU(self.hidden_size, self.hidden_size)
        self.out = nn.Linear(self.hidden_size, self.output_size)

    def forward(self, hidden, encoder_outputs):
        
        attn_weights = self.attn(hidden)
        attn_applied = torch.bmm(attn_weights.unsqueeze(1), encoder_outputs)
        attn_applied = F.softmax(self.attn2(attn_applied.squeeze(1)))
        attn_applied = torch.bmm(attn_applied.unsqueeze(1), encoder_outputs)
        attn_applied = attn_applied.squeeze(1)
        #output = torch.cat((input[0], attn_applied[0]), 1)
        output = self.attn_combine(attn_applied)
        output = F.tanh(output)
        output = self.out(output)
        #output = F.log_softmax(self.out(output[0]))
        
        return output, hidden, attn_weights

def train(input_variable, target_variable, encoder, decoder, linear, encoder_optimizer, 
    decoder_optimizer, linear_optimizer, criterion, max_length=T):

    encoder_optimizer.zero_grad()
    decoder_optimizer.zero_grad()
    linear_optimizer.zero_grad()
    #decoder2_optimizer.zero_grad()

    loss = 0
    
    lead_output = Variable(torch.Tensor().type('torch.cuda.FloatTensor'))
    lead_hidden = Variable(torch.Tensor().type('torch.cuda.FloatTensor'))

    for i in range(L):
        input_part = input_variable[i].clone()
        input_lead = input_part.view(N,T,D).transpose(0,1)

        encoder_outputs, encoder_hidden = encoder(input_lead)
        decoder_hidden = encoder_hidden
        decoder_output, decoder_hidden, attn_weights = decoder(decoder_hidden, encoder_outputs)

        lead_output = Variable(torch.cat((lead_output.data, decoder_output.data),1))
        lead_hidden = Variable(torch.cat((lead_hidden.data, decoder_hidden.data),1))

    lead_output = lead_output.view(N,L,100)
    #encoder2_outputs, encoder2_hidden = encoder2(lead_output)
    #decoder2_hidden = encoder2_hidden
    decoder2_output, decoder2_hidden, attn_weights = linear(lead_hidden, lead_output)
   
    loss = criterion(decoder2_output, target_variable)
    print(loss)
    loss.backward()

    encoder_optimizer.step()
    decoder_optimizer.step()
    linear_optimizer.step()

    return loss.data[0]

def test(input_variable, encoder, decoder, linearr):
    
    lead_output = Variable(torch.Tensor().type('torch.cuda.FloatTensor'))
    lead_hidden = Variable(torch.Tensor().type('torch.cuda.FloatTensor'))

    for i in range(L):
        input_part = input_variable[i].clone()
        input_lead = input_part.view(1,T,D).transpose(0,1).clone()
        encoder_outputs, encoder_hidden = encoder(input_lead)
        decoder_hidden = encoder_hidden
        decoder_output, decoder_hidden, attn_weights = decoder(decoder_hidden, encoder_outputs)

        lead_output = Variable(torch.cat((lead_output.data,decoder_output.data),1))
        lead_hidden = Variable(torch.cat((lead_hidden.data, decoder_hidden.data),1))
   
    lead_output = lead_output.view(1,L,100)
    
    decoder2_output, decoder2_hidden, attn_weights = linear(lead_hidden, lead_output)
    
    top_n, top_i = decoder2_output.data.topk(1)
    return top_i[0][0]

def trainIters(encoder, decoder, linear, learning_rate=0.01):

    n_epochs = 10
    current_loss = 0
    all_losses = []
    err_rate = []
    confusion = torch.zeros(6, 6)
    err = 0

    encoder_optimizer = torch.optim.Adam(encoder.parameters(), lr=learning_rate)
    decoder_optimizer = torch.optim.Adam(decoder.parameters(), lr=learning_rate)
    linear_optimizer = torch.optim.Adam(linear.parameters(), lr=learning_rate)
    #decoder2_optimizer = torch.optim.Adam(decoder2.parameters(), lr=learning_rate)

    criterion = nn.CrossEntropyLoss()

    for epoch in range(1, n_epochs+1):
        for step1,(batch_x, batch_y) in enumerate(train_loader):
            batch_x = batch_x*0.0048
            batch_x = Variable(batch_x.type('torch.cuda.FloatTensor'))
            batch_y = Variable(batch_y.type('torch.cuda.LongTensor'))
            print(batch_y)
            loss = train(batch_x.view(N,L,-1).transpose(0,1), batch_y, encoder,
                decoder, linear, encoder_optimizer, decoder_optimizer, linear_optimizer, criterion)
            current_loss += loss

        for step2,(test_x, test_y) in enumerate(test_loader):
            test_x = test_x*0.0048
            test_x = Variable(test_x.type('torch.cuda.FloatTensor'))
            test_y = test_y.type('torch.cuda.LongTensor')
            guess = test(test_x.view(1,L,-1).transpose(0,1), encoder, decoder, linear)
            #print('g',guess,'t',test_y[0])
            if guess != test_y[0]:
                    err += 1
        
            if epoch == n_epochs:
                confusion[guess][test_y[0]] += 1   

        print(current_loss/(step1+1))
        all_losses.append(current_loss/(step1+1))
        err_rate.append((1-err/16000)*100)
        print(err)
        print('%d epoch:, err number = %d, err rate = %.2f%%'%(epoch, err, ((1-err/16000)*100)))
    
        current_loss = 0
        err = 0

    plt.figure()
    plt.plot(all_losses)
    plt.title('loss')
    plt.figure()
    plt.plot(err_rate)
    plt.title('err')


    print(confusion)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    cax = ax.matshow(confusion.numpy())
    fig.colorbar(cax)

    plt.show()

hidden_size = 200
encoder = EncoderRNN(D, hidden_size)
decoder = AttnDecoderRNN(hidden_size, 100)
linear = LinearClass(100, 6)

if use_cuda:
    encoder = encoder.cuda()
    decoder = decoder.cuda()
    linear = linear.cuda()

trainIters(encoder, decoder, linear)
