-- Get the currently selected track
local track = reaper.GetSelectedTrack(0, 0)
if not track then
  reaper.ShowMessageBox("Please select a track.", "Error", 0)
  return
end

-- Start an undo block
reaper.Undo_BeginBlock()

-- Get the number of media items on the track
local itemCount = reaper.CountTrackMediaItems(track)

-- Iterate through each media item
for i = 0, itemCount - 1 do
  -- Get the media item
  local item = reaper.GetTrackMediaItem(track, i)
  
  -- Get the start and end positions of the media item
  local itemStart = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
  local itemLength = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
  local itemEnd = itemStart + itemLength
  
  -- Get the active take of the media item
  local take = reaper.GetActiveTake(item)
  if take then
    -- Get the name of the media item (take name)
    local takeName = reaper.GetTakeName(take)
    

    takeName = takeName:gsub("#.*", "") --去掉#和#后面的字符, 为了和load prof工具配合

    -- Create a region with the same name and length as the media item
    reaper.AddProjectMarker2(0, true, itemStart, itemEnd, takeName, -1, 0)
  end
end

-- End the undo block
reaper.Undo_EndBlock("Batch Create Regions from Media Items", -1)

-- Update the arrange view
reaper.UpdateArrange()
