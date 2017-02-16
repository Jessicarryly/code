require 'torch'

local DataLoader = torch.class('DataLoader')


function DataLoader:__init(kwargs)
  
  local N, T = self.batch_size, self.seq_length

  -- Just slurp all the data into memory
  local splits = {}
  local f = hdf5.open(h5_file, 'r')
  splits.train = f:read('/train'):all()
  splits.val = f:read('/val'):all()
  splits.test = f:read('/test'):all()

  self.x_splits = {}
  self.y_splits = {}
  self.split_sizes = {}
  for split, v in pairs(splits) do
    
    -- Chop out the extra bits at the end to make it evenly divide
    local vx = v[{{1, num - extra}}]:view(N, -1, T):transpose(1, 2):clone()
    local vy = v[{{2, num - extra + 1}}]:view(N, -1, T):transpose(1, 2):clone()
    
	local vx = v[{{1, num - extra}}]:view(N, -1, T):transpose(1, 2):clone()
    
	self.x_splits[split] = vx
    self.y_splits[split] = vy
    self.split_sizes[split] = vx:size(1)
  end

  self.split_idxs = {train=1, val=1, test=1}
end


function DataLoader:nextBatch(split)
  local idx = self.split_idxs[split]
  assert(idx, 'invalid split ' .. split)
  local x = self.x_splits[split][idx]
  local y = self.y_splits[split][idx]
  if idx == self.split_sizes[split] then
    self.split_idxs[split] = 1
  else
    self.split_idxs[split] = idx + 1
  end
  return x, y
end
