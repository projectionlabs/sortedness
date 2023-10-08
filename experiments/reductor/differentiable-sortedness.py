#  Copyright (c) 2023. Davi Pereira dos Santos
#  This file is part of the sortedness project.
#  Please respect the license - more about this in the section (*) below.
#
#  sortedness is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  sortedness is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with sortedness.  If not, see <http://www.gnu.org/licenses/>.
#
#  (*) Removing authorship by any means, e.g. by distribution of derived
#  works or verbatim, obfuscated, compiled or rewritten versions of any
#  part of this work is illegal and it is unethical regarding the effort and
#  time spent here.
#

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.optim as optim
from matplotlib import animation
from numpy import random
from scipy.spatial.distance import cdist
from scipy.stats import rankdata
from sklearn import datasets
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from torch import from_numpy, set_num_threads, tensor
from torch.utils.data import Dataset, DataLoader

from sortedness.embedding.surrogate import cau, wlossf9, wlossf8, har

# f = wlossf12 # 5.5
# f = wlossf11 # 5
# f = wlossf10 # 2
f = wlossf8     # 8   só local, mas peso pega todos vizinhos
f = wlossf9  # 6   é a proposta melhor fundamentada
# f = wlossf6 # 4  é o primeiro que plotei no email


threads = 1
# cuda.is_available = lambda: False
set_num_threads(threads)
n = 1797
k, gamma = 17, 10
smooothness_ranking, smooothness_tau, decay = [1], [5], 0
batch_size = [10]
update = 1
gpu = not True
a = 125
pdist = torch.nn.PairwiseDistance(p=2, keepdim=True)
seed = 0
lines = False
letters = True
fs = 16
rad = 120
alpha = 0.5
delta = 0

digits = datasets.load_digits()
n_samples = len(digits.images)
datax = digits.images.reshape((n_samples, -1))
datax = StandardScaler().fit_transform(datax)
datay = digits.target

# h = hdict.fromfile("/home/davi/train.csv")
# h.show()
# datax = h.df.loc[:, 'pixel0':].values
# datay = h.df.loc[:, 'label'].values

# mask = np.isin(datay, [1,0])
# datax = datax[mask]
# datay = datay[mask]

print(datax.shape)
print(datay.shape)

alph = datay  # "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
ax = [0, 0]

torch.manual_seed(seed)
rnd = random.default_rng(seed)
rnd = random.default_rng(seed)
X = datax[:n]
idxs = list(range(n))
X = X.astype(np.float32)


class Dt(Dataset):
    def __init__(self, X, y):
        # convert into PyTorch tensors and remember them
        self.X = torch.tensor(X, dtype=torch.float32)
        # self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        # this should return the size of the dataset
        return len(self.X)

    def __getitem__(self, idx):
        # this should return one sample from the dataset
        # features = self.X[idx]
        # target = self.y[idx]
        # return features, target, idx
        return idx


class M(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(X.shape[1], a), torch.nn.ReLU(),
            torch.nn.Linear(a, 2)
        )
        self.decoder = torch.nn.Sequential(
            torch.nn.Linear(2, a), torch.nn.ReLU(),
            torch.nn.Linear(a, X.shape[1])
        )

    def forward(self, x):
        return self.encoder(x)


model = M()
if gpu:
    model.cuda()
print(X.shape)
R = from_numpy(rankdata(cdist(X, X), axis=1)).cuda() if gpu else from_numpy(rankdata(cdist(X, X), axis=1))
T = from_numpy(X).cuda() if gpu else from_numpy(X)
w = cau(tensor(range(n)), gamma=gamma)
wharmonic = har(tensor(range(n)))

fig, axs = plt.subplots(1, 2, figsize=(12, 9))
ax[0], ax[1] = axs
ax[0].cla()
# encoded = model(T)
# D = pdist(encoded.unsqueeze(1), encoded.unsqueeze(0)).view(n, n)
# if gpu:
#     w = w.cuda()
# loss, ref = f(D, R, smooothness_ranking[0], smooothness_tau[0], ref=True, k=k, gamma=gamma, w=w)
# xcp = encoded.detach().cpu().numpy()

xcp = TSNE(random_state=42, n_components=2, verbose=0, perplexity=40, n_iter=300, n_jobs=-1).fit_transform(X)
D = from_numpy(rankdata(cdist(xcp, xcp), axis=1)).cuda() if gpu else from_numpy(rankdata(cdist(xcp, xcp), axis=1))
loss, ref_local, ref_global = f(D, R, smooothness_ranking[0], smooothness_tau[0], ref=True, k=k, gamma=gamma, w=w, wharmonic=wharmonic)

ax[0].scatter(xcp[:, 0], xcp[:, 1], s=rad, c=alph[idxs], alpha=alpha)
if lines:
    ax[0].plot(xcp[:, 0], xcp[:, 1], alpha=alpha)
if letters:
    for j in range(min(n, 50)):  # xcp.shape[0]):
        ax[0].text(xcp[j, 0] + delta, xcp[j, 1] + delta, alph[j], size=fs)
ax[0].title.set_text(f"{0}:  {ref_local:.8f}  {ref_global:.8f}")
print(f"{0:09d}:\toptimized sur: {loss:.8f}\tlocal/global:  {ref_local:.8f}  {ref_global:.8f}\t\t{smooothness_ranking[0]:.6f}\t{smooothness_tau[0]:.6f}")

optimizer = optim.RMSprop(model.parameters())
# optimizer = optim.ASGD(model.parameters())
# optimizer = optim.Rprop(model.parameters())
model.train()

c = [0]

if threads > 1:
    loader = [DataLoader(Dt(T, R), shuffle=True, batch_size=batch_size[0], num_workers=threads, pin_memory=gpu)]
else:
    loader = [DataLoader(Dt(T, R), shuffle=True, batch_size=batch_size[0], num_workers=1, pin_memory=gpu)]


def animate(i):
    c[0] += 1
    i = c[0]
    for idx in loader[0]:
        encoded = model(T)
        expected_ranking_batch = R[idx]
        D_batch = pdist(encoded[idx].unsqueeze(1), encoded.unsqueeze(0)).view(len(idx), -1)
        loss, ref_local_,ref_global_ = f(D_batch, expected_ranking_batch, smooothness_ranking[0], smooothness_tau[0], ref=i % update == 0, k=k, gamma=gamma, w=w, wharmonic=wharmonic)
        if ref_local_ != 0:
            ref_local = ref_local_
        if ref_global_ != 0:
            ref_global = ref_global_
        optimizer.zero_grad()
        (-loss).backward()
        optimizer.step()

    if i % update == 0:
        ax[1].cla()
        xcp = encoded.detach().cpu().numpy()
        ax[1].scatter(xcp[:, 0], xcp[:, 1], s=rad, c=alph[idxs], alpha=alpha)
        if lines:
            ax[1].plot(xcp[:, 0], xcp[:, 1], alpha=alpha)
        if letters:
            for j in range(min(n, 50)):  # xcp.shape[0]):
                ax[1].text(xcp[j, 0] + delta, xcp[j, 1] + delta, alph[j], size=fs)
        plt.title(f"{i}:  {ref_local:.8f}  {ref_global:.8f}", fontsize=20)
        smooothness_ranking[0] *= 1 - decay
        smooothness_tau[0] *= 1 - decay
    print(f"{i:09d}:\toptimized sur: {loss:.8f}\tlocal/global:  {ref_local:.8f}  {ref_global:.8f}\t\t{smooothness_ranking[0]:.6f}\t{smooothness_tau[0]:.6f}")

    return ax[1].step([], [])


mng = plt.get_current_fig_manager()
# mng.resize(*mng.window.maxsize())
with torch.enable_grad():
    anim = animation.FuncAnimation(fig, animate)
plt.show()
