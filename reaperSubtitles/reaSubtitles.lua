local defaultItemLength = 2
local retval, user_input = reaper.GetUserInputs("创建字幕", 1, "输入要显示的内容", "")

if retval then
    local cursor_position = reaper.GetCursorPosition()
    local track_count = reaper.CountTracks(0)
    if track_count > 0 then
        local track = reaper.GetSelectedTrack(0, 0)
        local item = reaper.AddMediaItemToTrack(track)
        reaper.SetMediaItemInfo_Value(item, "D_POSITION", cursor_position)
        reaper.SetMediaItemInfo_Value(item, "D_LENGTH", defaultItemLength)
        reaper.ULT_SetMediaItemNote(item, user_input)
        
        local new_take = reaper.AddTakeToMediaItem(item)
        reaper.GetSetMediaItemTakeInfo_String(new_take, "P_NAME", user_input, true)
        
        if new_take then
            local fx_name = "Video processor"
            local fxIndex = reaper.TakeFX_AddByName(new_take, fx_name, -1)
            
            -- If "Video processor" is not found, try "视频处理器"
            if fxIndex < 0 then
                fx_name = "视频处理器"
                fxIndex = reaper.TakeFX_AddByName(new_take, fx_name, -1)
            end
            
            if fxIndex >= 0 then
                local yPos = reaper.TakeFX_GetParam(new_take, fxIndex, 1)
                
                -- Check for overlapping items
                local item_count = reaper.CountTrackMediaItems(track)
                for i = 0, item_count - 1 do
                    local other_item = reaper.GetTrackMediaItem(track, i)
                    if other_item ~= item then
                        local other_pos = reaper.GetMediaItemInfo_Value(other_item, "D_POSITION")
                        local other_len = reaper.GetMediaItemInfo_Value(other_item, "D_LENGTH")
                        
                        if cursor_position < other_pos + other_len and cursor_position + defaultItemLength > other_pos then
                            yPos = yPos - 0.05
                        end
                    end
                end
                
                reaper.TakeFX_SetParam(new_take, fxIndex, 1, yPos)
            else
                reaper.ShowMessageBox("Failed to add FX.", "Error", 0)
            end
        else
            reaper.ShowMessageBox("Failed to add new take.", "Error", 0)
        end
        
        reaper.UpdateArrange()
    else
        reaper.ShowMessageBox("No tracks available to add an item.", "Error", 0)
    end
else
    reaper.ShowMessageBox("User input was cancelled.", "Cancelled", 0)
end