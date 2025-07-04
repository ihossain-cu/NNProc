import os
import sys
from tqdm import tqdm
import torch
import torch.optim.lr_scheduler as lr_scheduler
from dataset import ShapeDataset
from model import NNProc, NNProcLoss
from utils import print_report


def run_epoch(data_loader, model, loss_fn, optim, scheduler, do_backward=False):
    epoch_loss = 0.0
    it = iter(data_loader)
    for i, batch in enumerate(tqdm(it, file=sys.stdout)):
        if do_backward:
            model.train()
            optim.zero_grad()
        else:
            model.eval()
        param_recon, voxel_recon, p_z, mu, logvar = model(batch['prm'], batch['vxl'])
        loss = loss_fn(param_recon, voxel_recon, p_z, mu, logvar, batch['prm'], batch['vxl'])
        if do_backward:
            loss.backward()
            optim.step()
        epoch_loss += loss.item()
    epoch_loss /= len(data_loader.sampler)
    scheduler.step()
    return epoch_loss


def optimize_model(shape):
    data_file = os.path.join('/', 'mnt', 'Research', 'Data', 'dataset', 'pml', shape + '.hdf5')
    train_loader, valid_loader = ShapeDataset(data_file).get_data_loader(batch_size=64)
    model = NNProc(shape)
    loss_fn = NNProcLoss(shape)
    optim = torch.optim.Adam(model.parameters())
    num_epochs = 300
    scheduler = lr_scheduler.LinearLR(optim, start_factor=1.0, end_factor=0.1, total_iters=num_epochs)
    for e in range(num_epochs):
        train_loss = run_epoch(train_loader, model, loss_fn, optim, scheduler, True)
        valid_loss = run_epoch(valid_loader, model, loss_fn, optim, scheduler)
        print('Epoch {}: T Loss: {:.5f}, V Loss: {:.5f}'.format(e + 1, train_loss, valid_loss))

        with torch.no_grad():
            print_report(
                shape,
                model.param_dec.predict(
                    model.voxel_enc.predict(valid_loader.dataset.vxl[valid_loader.sampler.indices].numpy())
                ),
                [x[valid_loader.sampler.indices].numpy() for x in valid_loader.dataset.prm]
            )
            torch.cuda.empty_cache()

    #torch.save(model.state_dict(), os.path.join('models', shape + '_model.pt'))


if __name__ == "__main__":
    for shape in ['bed', 'chair', 'shelf', 'sofa']:
    #for shape in ['table']:
        optimize_model(shape)
