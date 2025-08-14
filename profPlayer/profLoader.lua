-- Import necessary REAPER functionalities
local log_data = {}
local existingTracks = {}
local defaultItemLength = 0.1
local defaultStartingPos = 5
local currentTimestamp = ""
local currentTimeOrder = 0

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

-- function create_wwise_media_item(entry, pos)
--     local track_name = extract_first_word(entry["Description"])
--     local wwiseTrack = nil
--     for k, v in pairs(my_table) do
--         if k == track_name then
--             wwiseTrack = v
--     if wwiseTrack == nil then
--         wwiseTrack = AddWwiseTrack(track_name) -- Create a new Wwise track
--         existingTracks[track_name] = wwiseTrack
--     local name = entry["Object Name"]
--     local mediaItem = CreatMeidaItem(wwiseTrack, name, parseTable(entry), pos)
-- end


function create_wwise_media_item(entry, pos)
    local track_name = extract_first_word(entry["Description"])
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
    local mediaItem = CreateMediaItem(wwiseTrack, name, parseTable(entry), pos)
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

function CreateMediaItem(track,nameStr,notesStr, pos)
    local wwiseItem = reaper.AddMediaItemToTrack(track)
    reaper.GetSetMediaItemInfo_String(wwiseItem,"P_NAME",nameStr,true)
    reaper.GetSetMediaItemInfo_String(wwiseItem,"P_NOTES",notesStr,true)
    reaper.SetMediaItemInfo_Value(wwiseItem,"D_LENGTH",defaultItemLength)
    reaper.SetMediaItemInfo_Value(wwiseItem,"D_POSITION",pos)
    local wwiseTake = reaper.AddTakeToMediaItem(wwiseItem)
    reaper.GetSetMediaItemTakeInfo_String(wwiseTake,"P_NAME",nameStr,true)
end



local user_input, file_path = reaper.GetUserInputs("Enter log file path", 1, "Path:", "")

if file_path:sub(1, 1) == '"' and file_path:sub(-1, -1) == '"' then
    file_path = file_path:sub(2, -2)  -- Remove the first and last characters
end
-- file_path = "C:\\Users\\Administrator\\Desktop\\new.txt"
if file_path then
    log_data = read_log_file(file_path)
    recall_api_calls(log_data)
end


