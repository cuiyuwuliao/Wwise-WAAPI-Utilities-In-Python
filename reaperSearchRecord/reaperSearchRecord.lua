-- local function promptUserInput()
--     -- Default values configuration
--     local defaults = {
--         track_name = "@W_PostEvent",
--         prefix = "Play_UI",
--         export_path = "D:\\QA_Video",
--         record_dupe = 0,
--         pre_length = 2,
--         record_length = 4
--     }
    
--     -- Build the input prompt
--     local title = "导出设置 (留空使用默认值)"
--     local labels = "Track Name,Prefix,Export Path,Duplicate Count,Pre Length,Record Length"
--     local default_values = table.concat({
--         defaults.track_name,
--         defaults.prefix,
--         defaults.export_path,
--         defaults.record_dupe,
--         defaults.pre_length,
--         defaults.record_length
--     }, ",")
    
--     -- Show input dialog
--     local ret, user_input = reaper.GetUserInputs(title, 6, labels, default_values)
--     if not ret then return nil end  -- User canceled
    
--     -- Robust CSV parsing that handles all cases
--     local values = {}
--     local pos = 1
--     local len = #user_input

--     for i = 1, 6 do
--         local start_pos = pos
--         local end_pos = len + 1  -- Default to end of string
        
--         -- Find next comma (but not if inside quotes)
--         local comma_pos = user_input:find(",", pos, true)
--         if comma_pos then
--             end_pos = comma_pos
--             pos = comma_pos + 1
--         else
--             pos = len + 1
--         end
        
--         -- Extract and clean the value
--         local value = user_input:sub(start_pos, end_pos - 1)
--         value = value:gsub("^%s*(.-)%s*$", "%1")  -- Trim whitespace
--         if value == "" then value = nil end
        
--         values[i] = value
--     end
    
--     -- Return values with defaults for empty fields
--     return values[1] or defaults.track_name,
--            values[2] or defaults.prefix,
--            values[3] or defaults.export_path,
--            tonumber(values[4]) or defaults.record_dupe,
--            tonumber(values[5]) or defaults.pre_length,
--            tonumber(values[6]) or defaults.record_length
-- end
-- local track_name, prefix, exportPath, recordDupe, preLength, recordLength = promptUserInput()
--     local defaults = {

--     }
local track_name = "@W_PostEvent"
local prefix = "Play_UI"
local exportPath = "D:\\QA_Video"
local recordDupe = 0
local preLength = 2
local recordLength = 4
reaper.ShowConsoleMsg(track_name)



-- Global dictionary to store item information
globalItemInfo = {}

function getRegionNameByTime(time)
    
    local markeridx, regionidx = reaper.GetLastMarkerAndCurRegion(reaper.EnumProjects(-1), time)
    if regionidx >= 0 then
        local retval, is_region, pos, end_pos, name, markrgn_idx = reaper.EnumProjectMarkers(regionidx)
        if is_region then
            return name
        end
    end
    return ""
end

-- Function to get track by name
local function getTrackByName(name)
    local track_count = reaper.CountTracks(0)
    for i = 0, track_count - 1 do
        local track = reaper.GetTrack(0, i)
        local retval, current_name = reaper.GetTrackName(track)
        if retval and current_name == name then
            reaper.ShowConsoleMsg("found event Track" .. "\n")
            return track, i  -- Return track and its index
        end
    end
    return nil, nil
end

-- Get the track
local track, track_index = getTrackByName(track_name)

-- Function to display Object Name from item notes along with item's position
local function GetObjectInfo(track, track_index)
    if track then
        local item_count = reaper.CountTrackMediaItems(track)
        reaper.ShowConsoleMsg("found " .. item_count .. " items\n")
        for i = 0, item_count - 1 do
            local item = reaper.GetTrackMediaItem(track, i)
            local retval, item_note = reaper.GetSetMediaItemInfo_String(item, "P_NOTES", "", false)
            if retval then
                local object_name = item_note:match('Object Name: "([^"]+)"')
                local item_position = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
                
                if object_name then
                    globalItemInfo[#globalItemInfo + 1] = {
                        track_index = track_index,
                        item_index = i,
                        position = item_position,
                        object_name = object_name,
                        item_note = item_note
                    }
                end
            end
        end
    else
        reaper.ShowConsoleMsg("Track not found: " .. track_name .. "\n")
    end
end

-- Display Object Names from item notes on the track
GetObjectInfo(track, track_index)

-- Function to export item
function ExportItem(wavFilePath, itemPosition, length)
    local pos_start = itemPosition - preLength
    local pos_end = itemPosition + length
    local orig_start, orig_end = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    
    reaper.GetSet_LoopTimeRange(true, false, pos_start, pos_end, false)

    local directory = wavFilePath:match("(.+)[\\/]") 
    local file_name = wavFilePath:match("([^\\/]+)$") 

    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", directory, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true)

    reaper.Main_OnCommand(42230, 0)
    
    reaper.GetSet_LoopTimeRange(true, false, orig_start, orig_end, false)
end

-- Function to export all objects
function exportAllObjects(wavFilePath, length, numDupe, prefix)
    local exportedNames = {}

    for i = 1, #globalItemInfo do
        local info = globalItemInfo[i]
        if info then
            if prefix and not info.object_name:find("^" .. prefix) then
                goto continue
            end
            
            local exportName = info.object_name
            local count = 0
            local finalName = exportName
            
            while true do
                -- Construct the full export path
                local regionName = getRegionNameByTime(info.position)
                local exportPath = wavFilePath
                if regionName ~= "" then
                    exportPath = exportPath .. "\\" .. regionName
                end
                exportPath = exportPath .. "\\" .. finalName

                -- Check if the full path has already been exported
                if not exportedNames[exportPath] then
                    exportedNames[exportPath] = true
                    ExportItem(exportPath, info.position, length)
                    break
                else
                    count = count + 1
                    if numDupe ~= -1 and count >= numDupe then
                        break
                    end
                    finalName = exportName .. "_" .. count
                end
            end
        end
        
        ::continue::
    end
end




local today = os.date("%Y-%m-%d")
local fullPath = exportPath .. "\\" .. today
-- Call export function
exportAllObjects(fullPath, recordLength, recordDupe, prefix)


