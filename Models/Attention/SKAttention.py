import numpy as np
import torch
from torch import nn
from torch.nn import init
from collections import OrderedDict



class SKAttention(nn.Module):

    def __init__(self, channel_in=2048,channel=512,kernels=[12, 24, 36],reduction=16,group=1,L=32):
        super().__init__()
        self.channel = channel
        self.d=max(L,channel//reduction)
        self.convs=nn.ModuleList([])
        self.convs.append(
                nn.Sequential(OrderedDict([
                    ('conv',nn.Conv2d(channel_in,channel,kernel_size=1,bias=False,groups=group)),
                    ('bn',nn.BatchNorm2d(channel)),
                    ('relu',nn.ReLU())
                ]))
            )
        for k in kernels:
            self.convs.append(
                nn.Sequential(OrderedDict([
                    ('conv',nn.Conv2d(channel_in,channel,kernel_size=3,padding=k, dilation=k, bias=False,groups=group)),
                    ('bn',nn.BatchNorm2d(channel)),
                    ('relu',nn.ReLU())
                ]))
            )
        self.fc=nn.Linear(channel,self.d)
        self.fcs=nn.ModuleList([])
        for i in range(len(kernels)+1):
            self.fcs.append(nn.Linear(self.d,channel))
        self.softmax=nn.Softmax(dim=0)

        self.mlp = nn.Sequential(nn.Conv2d(channel, 256, 1, bias=False),
                                nn.BatchNorm2d(256),
                                nn.ReLU(inplace=True),
                                nn.Conv2d(256, 128, 1, bias=False),
                                nn.BatchNorm2d(128),
                                nn.ReLU(inplace=True))



    def forward(self, x):
        bs, _, _, _ = x.size()
        c = self.channel
        conv_outs=[]
        ### split
        for conv in self.convs:
            conv_outs.append(conv(x))
        feats=torch.stack(conv_outs,0)#k,bs,channel,h,w

        ### fuse
        U=sum(conv_outs) #bs,c,h,w

        ### reduction channel
        S=U.mean(-1).mean(-1) #bs,c
        Z=self.fc(S) #bs,d

        ### calculate attention weight
        weights=[]
        for fc in self.fcs:
            weight=fc(Z))
            weights.append(weight.view(bs,c,1,1)) #bs,channel
        attention_weughts=torch.stack(weights,0)#k,bs,channel,1,1
        attention_weughts=self.softmax(attention_weughts)#k,bs,channel,1,1

        ### fuse
        V=(attention_weughts*feats).sum(0)
        mlp = self.mlp(V)
        return V, mlp

        




if __name__ == '__main__':
    input=torch.randn(50,512,7,7)
    se = SKAttention(channel=512,reduction=8)
    output=se(input)
    print(output.shape)

    