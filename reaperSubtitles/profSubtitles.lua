-- Import necessary REAPER functionalities
local log_data = {}
local existingTracks = {}
local defaultItemLength = 1
local defaultStartingPos = 5
local currentTimestamp = ""
local currentTimeOrder = 0
local NZDictionary = {}
local filterWord = "Play_"
local mediaItems = {}
local occupiedYPositions = {}

function getNzId(eventName)
    for key, value in pairs(NZDictionary) do
        if value == eventName then
            return key
        end
    end
    return nil
end


function extract_sound_id(input_string)
    local pattern = "%$NZID:([^%s]+)"
    local sound_id = input_string:match(pattern)
    if sound_id then
        return true, sound_id
    else
        return false, ''
    end
end


function buildNZDictionary()
    isConnected = reaper.AK_Waapi_Connect("localhost", 8080)
    if not isConnected then
        reaper.ShowConsoleMsg("Failed to connect to WAAPI. Please ensure Wwise is running and WAAPI is enabled.\n")
    else
        reaper.ShowConsoleMsg("Connected to WAAPI.\n")
    end

    local args = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(args, "waql", reaper.AK_AkVariant_String("$ from type Event"))

    local fieldsToReturn = reaper.AK_AkJson_Array()
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("name"))
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("notes"))

    local options = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(options, "return", fieldsToReturn)

    local result = reaper.AK_Waapi_Call("ak.wwise.core.object.get", args, options)
    local status = reaper.AK_AkJson_GetStatus(result)

    if status then
        local objects = reaper.AK_AkJson_Map_Get(result, "return")
        local numObjects = reaper.AK_AkJson_Array_Size(objects)

        for i = 0, numObjects - 1 do
            local event = reaper.AK_AkJson_Array_Get(objects, i)
            local eventName = reaper.AK_AkJson_Map_Get(event, "name")
            local eventNotes = reaper.AK_AkJson_Map_Get(event, "notes")
            local rt, NzId = extract_sound_id(reaper.AK_AkVariant_GetString(eventNotes))
            NzId = NzId:match("^%s*(.-)%s*$") -- Trim whitespace
            if rt then
                NZDictionary[NzId] = reaper.AK_AkVariant_GetString(eventName)
            end
        end
        
        reaper.ShowConsoleMsg("已关联NZID信息\n")
    else
        reaper.ShowConsoleMsg("Failed to retrieve events.\n")
    end
    reaper.AK_Waapi_Disconnect()
    isConnected = false
    reaper.ShowConsoleMsg("Disconnected from WAAPI.\n")
end


function parse_log_entry(entry)
    local parts = {}
    local expected_parts = 8  -- Number of expected parts

    -- Initialize parts with empty strings for all expected values
    for i = 1, expected_parts do
        table.insert(parts, "")
    end

    local index = 1  -- Index to track where to insert valid parts

    for part in string.gmatch(entry, "[^\t]*") do
        if index <= expected_parts then
            parts[index] = part  -- Insert the part into the correct index
            index = index + 1    -- Move to the next index
        else
            -- Optionally handle excess parts here
            print("Warning: Excess part detected - " .. part)
        end
    end

    if currentTimestamp == parts[1] then 
        currentTimeOrder = currentTimeOrder + 1
    else 
        currentTimestamp = parts[1]
        currentTimeOrder = 0
    end

    local result = {
        Timestamp = parts[1],
        Type = parts[2],
        Description = parts[3],
        ["Object Name"] = parts[4],
        ["Game Object Name"] = parts[5],
        ["Object ID"] = parts[6],
        ["Game Object ID"] = parts[7],
        Scope = parts[8],
        Order = currentTimeOrder
    }

    if result["Description"]:find("SetSwitch") then
        result["Game Object ID"] = "22334"
    end

    if result["Type"] ~= "API Call" then
        return nil
    end 

    return result
end

function TableContains(table, key)
    return table[key] ~= nil and table[key] ~= false
end

function convertTimestampToSeconds(timestamp)
    -- Split the timestamp into components
    local hours, minutes, seconds = timestamp:match("^(%d+):(%d+):(%d+%.%d+)$")
    -- Convert string components to numbers
    hours = tonumber(hours) or 0
    minutes = tonumber(minutes) or 0
    seconds = tonumber(seconds) or 0
    -- Calculate total seconds
    return hours * 3600 + minutes * 60 + seconds
end

function parseTable(input)
    -- If input is a table, convert it to a string
    if type(input) == "table" then
        local result = "{"
        for k, v in pairs(input) do
            if type(v) == "table" then
                v = convert(v)  -- Recursively convert sub-tables
            elseif type(v) == "string" then
                v = '"' .. v .. '"'  -- Quote strings
            end
            result = result .. tostring(k) .. ": " .. tostring(v) .. ", "
        end
        -- Remove the trailing comma and space
        if next(input) ~= nil then
            result = result:sub(1, -3)
        end
        result = result .. "}"
        return result

    -- If input is a string, convert it to a table
    elseif type(input) == "string" then
        local tbl = {}
        -- Remove the braces and split by comma
        local trimmed = input:match("^%s*{(.*)}%s*$")
        for pair in trimmed:gmatch("[^,]+") do
            local k, v = pair:match("(%w+):%s*(.*)")
            if v then
                -- Remove quotes if present
                v = v:gsub('^"(.+)"$', '%1')
                tbl[k] = tonumber(v) or v  -- Convert to number if possible
            end
        end
        return tbl
    else
        error("Input must be a string or a table.")
    end
end

function read_log_file(file_path)
    local log_data = {}
    local file = io.open(file_path, "r")
    if not file then
        print("Error: The file '" .. file_path .. "' was not found.")
        return log_data
    end

    for line in file:lines() do
        local formatted_line = line:gsub("^%s*(.-)%s*$", "%1")
        table.insert(log_data, formatted_line)
    end
    file:close()
    
    return log_data
end

function recall_api_calls(log_data)
    local parsed_entries = {}
    for i = 3, #log_data do
        entry = parse_log_entry(log_data[i])
        if entry ~= nil then
            table.insert(parsed_entries, entry)
        end
    end
    table.sort(parsed_entries, function(a, b) return a.Timestamp < b.Timestamp end)

    -- Find the earliest timestamp
    local earliest_timestamp = convertTimestampToSeconds(parsed_entries[1].Timestamp)
    

    -- Create media items based on log entries with adjusted positions
    for _, entry in ipairs(parsed_entries) do
        local pos = convertTimestampToSeconds(entry.Timestamp) - earliest_timestamp + defaultStartingPos
        create_wwise_media_item(entry, pos) -- Pass adjusted position
    end
end

function extract_first_word(input)
    -- Trim leading and trailing whitespace
    input = input:match("^%s*(.-)%s*$")  -- Trim whitespace
    local first_word = input:match("^(%S+)")  -- Get the first non-space word
    if first_word:sub(-1) == ":" then
        first_word = first_word:sub(1, -2)  -- Return the string without the last character
    end
    return first_word
end

function create_wwise_media_item(entry, pos)
    local track_name = extract_first_word(entry["Description"])
    if track_name ~= "PostEvent" and track_name ~= "SetSwitch" and track_name ~= "SetState" and track_name ~= "ExecuteActionOnEvent"then
        return nil
    end
    local wwiseTrack = nil
    -- Check if the track already exists
    for k, v in pairs(existingTracks) do
        if k == track_name then
            wwiseTrack = v
            break  -- Exit the loop if the track is found
        end
    end
    -- If the track was not found, create a new one
    if wwiseTrack == nil then
        wwiseTrack = AddWwiseTrack(track_name)  -- Create a new Wwise track
        existingTracks[track_name] = wwiseTrack
    end
    local name = entry["Object Name"]
    if track_name == "PostEvent" and string.find(string.lower(name), string.lower(filterWord)) == nil then
        return nil
    end
    local mediaItem = nil
    if track_name == "PostEvent" then
        mediaItem = CreateMediaItem_Event(wwiseTrack, name, parseTable(entry), pos)
    else
        mediaItem = CreateMediaItem(wwiseTrack, name, parseTable(entry), pos)
    end

    return mediaItem  -- Optional: Return the created media item if needed
end

-- Function to add a new Wwise track
function AddWwiseTrack(track_name)
    local targetTrack = reaper.GetSelectedTrack(rproj,0)
    local wwiseTrack
    local targetTrackIdx
    if targetTrack == nil then
        targetTrackIdx = reaper.CountTracks(rproj)
        reaper.InsertTrackAtIndex(targetTrackIdx,true)
        wwiseTrack = reaper.GetTrack(rproj,targetTrackIdx)
    else
        targetTrackIdx = reaper.GetMediaTrackInfo_Value(targetTrack,"IP_TRACKNUMBER")
        reaper.InsertTrackAtIndex(targetTrackIdx-1,true)
        wwiseTrack = reaper.GetTrack(rproj,targetTrackIdx-1)
    end
    reaper.GetSetMediaTrackInfo_String(wwiseTrack,"P_NAME","@W_"..track_name,true)
    return wwiseTrack
end

function CreateMediaItem_Event(track, nameStr, notesStr, pos)
    local wwiseItem = reaper.AddMediaItemToTrack(track)
    NzId = getNzId(nameStr)
    if NzId == nil then
        NzId = ""
    else
        NzId = nameStr.."#"..NzId.."#"
    end
    reaper.GetSetMediaItemInfo_String(wwiseItem, "P_NAME", nameStr, true)
    notesStr = "#" .. nameStr .. "#"
    reaper.GetSetMediaItemInfo_String(wwiseItem, "P_NOTES", notesStr, true)
    reaper.SetMediaItemInfo_Value(wwiseItem, "D_LENGTH", defaultItemLength)
    reaper.SetMediaItemInfo_Value(wwiseItem, "D_POSITION", pos)
    local wwiseTake = reaper.AddTakeToMediaItem(wwiseItem)
    local fxIndex = 0
    if wwiseTake then
        local fx_name = "Video processor"
        fxIndex = reaper.TakeFX_AddByName(wwiseTake, fx_name, -1)
    else
        reaper.ShowMessageBox("Failed to add new take.", "Error", 0)
    end

    reaper.GetSetMediaItemTakeInfo_String(wwiseTake, "P_NAME", NzId, true)


    for key, value in pairs(occupiedYPositions) do
        if pos - defaultItemLength > value then
            occupiedYPositions[key] = nil
        end
    end
    if fxIndex >= 0 then
        yPos = reaper.TakeFX_GetParam(wwiseTake, fxIndex, 1)
        while occupiedYPositions[yPos] do
            yPos = yPos - 0.05  -- Decrement yPos until an unoccupied position is found
        end
        reaper.TakeFX_SetParam(wwiseTake, fxIndex, 1, yPos)
    end
    occupiedYPositions[yPos] = pos
end

function CreateMediaItem(track,nameStr,notesStr, pos)
    local wwiseItem = reaper.AddMediaItemToTrack(track)
    reaper.GetSetMediaItemInfo_String(wwiseItem,"P_NAME",nameStr,true)
    reaper.GetSetMediaItemInfo_String(wwiseItem,"P_NOTES",notesStr,true)
    reaper.SetMediaItemInfo_Value(wwiseItem,"D_LENGTH",defaultItemLength)
    reaper.SetMediaItemInfo_Value(wwiseItem,"D_POSITION",pos)
    local wwiseTake = reaper.AddTakeToMediaItem(wwiseItem)
    reaper.GetSetMediaItemTakeInfo_String(wwiseTake,"P_NAME",nameStr,true)
end

buildNZDictionary()

local retval1, file_path = reaper.GetUserInputs("Enter log file path", 1, "Path:", "")
if not retval1 then
    reaper.ShowMessageBox("User canceled the input dialog for file path.", "Error", 0)
    return
end

-- Second, get the search word from the user
local retval2, searchWord = reaper.GetUserInputs("Enter search word", 1, "Search Word:", "Play_")
if not retval2 then
    reaper.ShowMessageBox("User canceled the input dialog for search word.", "Error", 0)
    return
end
filterWord = searchWord

-- Remove quotes from file path if necessary
if file_path:sub(1, 1) == '"' and file_path:sub(-1, -1) == '"' then
    file_path = file_path:sub(2, -2)
end

-- Proceed with the rest of your script logic
log_data = read_log_file(file_path)
recall_api_calls(log_data)
