-- Import necessary REAPER functionalities
defaultItemLength =3
wwiseTrackName = "@W_"
local isConnected = false
local playPosition = 0
local isStop
local playingIDs = {}
local registeredObj = {}
local listenerIds = {}
local NZDictionary = {}

-- NZ项目的默认Listener，保证就算没有登记listener也可以出声, 使用parse过的entry
local SetDefaultListener = {
    ["Game Object Name"] = "", 
    ["Object Name"] = "", 
    ["Game Object ID"] = "4294967296", 
    ["Object ID"] = "", 
    Type = "API Call", 
    Description = "SetDefaultListeners: PlayerCameraManager0.AkComponent_0", 
    Scope = "Game Object", 
    Timestamp = "0:34:23.040", 
    Order = 2
}

local RegisterDefaultListener = {
    ["Game Object Name"] = "PlayerCameraManager0.AkComponent_0", 
    ["Object Name"] = "", 
    ["Game Object ID"] = "2570276691456", 
    ["Object ID"] = "", 
    Type = "API Call", 
    Description = "RegisterGameObj: PlayerCameraManager0.AkComponent_0 (ID:1886248448)", 
    Scope = "Game Object", 
    Timestamp = "0:34:23.040", 
    Order = 1
}
-- Function to connect to WAAPI
function connect()
    isConnected = reaper.AK_Waapi_Connect("localhost", 8080)
    if not isConnected then
        reaper.ShowConsoleMsg("Failed to connect to WAAPI. Please ensure Wwise is running and WAAPI is enabled.\n")
    else
        reaper.ShowConsoleMsg("Connected to WAAPI.\n")
    end
    return isConnected
end

-- Function to disconnect from WAAPI
function disconnect()
    reaper.AK_Waapi_Disconnect()
    isConnected = false
    reaper.ShowConsoleMsg("Disconnected from WAAPI.\n")
end

function itemInTable(table)
    reaper.ShowConsoleMsg("遍历开始")
    for key,value in pairs(table) do
        reaper.ShowConsoleMsg("遍历结果"..tostring(value).." , ")
    end
    reaper.ShowConsoleMsg("\n")
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
    if not isConnected then
        reaper.ShowConsoleMsg("Not connected to WAAPI. Please connect first.\n")
        return
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
end

-- Function to extract values between # characters without the symbols
function extract_hash_values(input_string)
    local values = {}
    for value in string.gmatch(input_string, "#(.-)#") do
        if NZDictionary[value] then
            value = NZDictionary[value]
        end
        table.insert(values, value)
    end
    return values
end

function process_event_2D(event)
    -- Extract values from the event string
    local extracted_events = extract_hash_values(event)

    -- -- Register game objects
    -- local listenerArg = reaper.AK_AkJson_Map()
    -- reaper.AK_AkJson_Map_Set(listenerArg, "gameObject", reaper.AK_AkVariant_Int(22334))
    -- reaper.AK_AkJson_Map_Set(listenerArg, "name", reaper.AK_AkVariant_String("ReaperPlayer"))
    -- reaper.AK_Waapi_Call("ak.soundengine.registerGameObj", listenerArg, reaper.AK_AkJson_Map())

    -- Post each extracted event
    for _, extracted_event in ipairs(extracted_events) do
        local playArg = reaper.AK_AkJson_Map()
        reaper.AK_AkJson_Map_Set(playArg, "gameObject", reaper.AK_AkVariant_Int(22334))
        reaper.AK_AkJson_Map_Set(playArg, "event", reaper.AK_AkVariant_String(extracted_event))
        reaper.AK_Waapi_Call("ak.soundengine.postEvent", playArg, reaper.AK_AkJson_Map())
    end
end

function addToTable(table, key)
    table[key] = true
end

function removeFromTable(table, key)
    table[key] = false
end

function TableContains(table, key)
    return table[key] ~= nil and table[key] ~= false
end

function print_table(t)
    for key, value in pairs(t) do
        -- Check if the value is a table itself
        if type(value) == "table" then
            reaper.ShowConsoleMsg(key .. ":")
            reaper.ShowConsoleMsg(value)
        else
            reaper.ShowConsoleMsg(key .. ": " .. tostring(value))
        end
        reaper.ShowConsoleMsg("\n")
    end
end

function parseTable(input)
    local result = {}
    -- Remove the curly braces
    input = input:sub(2, -2)

    -- Use pattern to match key-value pairs properly
    for key, value in input:gmatch("([^:]+):%s*\"([^\"]*)\"") do
        key = key:gsub("^%s*(.-)%s*$", "%1") -- Trim whitespace from key
        key = key:gsub(", ", "")
        result[key] = value
    end

    -- Handle keys with no quoted values (like empty strings)
    for key, value in input:gmatch("([^:]+):%s*([^,}]+)") do
        key = key:gsub("^%s*(.-)%s*$", "%1") -- Trim whitespace from key
        key = key:gsub(", ", "")
        value = value:gsub("^%s*(.-)%s*$", "%1") -- Trim whitespace from value
        if value ~= "" and not result[key] then
            result[key] = value
        end
    end

    return result
end

-- Function to execute API calls based on log entry
function execute_api_from_log(entry)
    local api_call = entry["Description"]
    local gameObject_id = tonumber(entry["Game Object ID"]) or 0
    if gameObject_id >= 100000 then
        gameObject_id = math.floor(gameObject_id % 100000)  -- Get the last five digits as an integer
    end
    local object_name = entry["Object Name"]
    local object_id = tonumber(entry["Object ID"]) or 0
    if object_id >= 100000 then
        object_id = math.floor(object_id % 100000)  -- Get the last five digits as an integer
    end

    local name = entry["Game Object Name"] or "UnnamedObject"
    name = name:gsub('^"%s*(.-)%s*"$', '%1')
    -- Extract relevant data and convert to AK variants
    local position_data = extract_position_data(api_call)  -- Ensure this returns an AK variant if needed
    local scaling_factor = reaper.AK_AkVariant_Double(extract_scaling_factor(api_call))
    local rtpc = reaper.AK_AkVariant_Double(extract_rtpc_value(api_call))
    switchValue = extract_switch(api_call)
    switch = "Unkown switch"
    if tonumber(switchValue) then
        switch = reaper.AK_AkVariant_Int(switchValue)
    else
        switch = reaper.AK_AkVariant_String(switchValue)
    end

    local arg = reaper.AK_AkJson_Map()  -- Create a JSON map for API call

    if api_call:find("RegisterGameObj") then
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_AkJson_Map_Set(arg, "name", reaper.AK_AkVariant_String(name))
        reaper.AK_Waapi_Call("ak.soundengine.registerGameObj", arg, reaper.AK_AkJson_Map())
        registeredObj[name] = gameObject_id

    elseif api_call:find("SetPosition") then
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_AkJson_Map_Set(arg, "position", position_data)  -- Ensure position_data is an AK variant
        reaper.AK_Waapi_Call("ak.soundengine.setPosition", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("SetDefaultListeners") then
        local listeners = reaper.AK_AkJson_Array()
        local listenersName = extract_listeners(api_call)
        for i = 1, #listenersName do
            name = listenersName[i]
            id = registeredObj[name] or 0
            table.insert(listenerIds, id)
            reaper.AK_AkJson_Array_Add(listeners, reaper.AK_AkVariant_Int(id))
        end
        reaper.AK_AkJson_Map_Set(arg, "listeners", listeners)  -- Already an AK variant
        reaper.AK_Waapi_Call("ak.soundengine.setDefaultListeners", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("PostEvent") then
        reaper.AK_AkJson_Map_Set(arg, "event", reaper.AK_AkVariant_String(object_name))
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_Waapi_Call("ak.soundengine.postEvent", arg, reaper.AK_AkJson_Map())
        -- jresult = reaper.AK_AkJson_Map_Get(result,"return")
        -- if jresult then
        --     local wwisePlayingID, err
        --     -- Use pcall to protect the function call
        --     local success, res = pcall(function()
        --         return reaper.AK_AkVariant_GetString(jresult)
        --     end)
        --     if success then
        --         wwisePlayingID = res
        --         reaper.ShowConsoleMsg("Wwise Playing ID: " .. wwisePlayingID)
        --     else
        --         reaper.ShowConsoleMsg("Error: " .. result) -- result contains the error message
        --     end 
        -- end
        -- 
        -- reaper.ShowConsoleMsg(tostring(jresult))
        -- 
        -- wwisePlayingID = jresult.AK_AkVariant_GetString(jname)
        -- reaper.ShowConsoleMsg(wwisePlayingID)


    elseif api_call:find("SetAttenuationScalingFactor") then
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_AkJson_Map_Set(arg, "attenuationScalingFactor", scaling_factor)
        reaper.AK_Waapi_Call("ak.soundengine.setScalingFactor", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("SetSwitch") then
        reaper.AK_AkJson_Map_Set(arg, "switchGroup", reaper.AK_AkVariant_String(object_name))
        reaper.AK_AkJson_Map_Set(arg, "switchState", switch)
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_Waapi_Call("ak.soundengine.setSwitch", arg, reaper.AK_AkJson_Map())
    
    elseif api_call:find("SetGameObjectAuxSend") then
        auxName, auxValue = extract_aux_send(api_call)
        if auxBus ~= "(Unknown aux bus)" and auxBus ~= nil then
            reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
            arg_map = reaper.AK_AkJson_Map()
            listener = listenerIds[1] or 0
            reaper.AK_AkJson_Map_Set(arg_map, "listener", reaper.AK_AkVariant_Int(listener))
            reaper.AK_AkJson_Map_Set(arg_map, "auxBus", reaper.AK_AkVariant_String(auxName))
            reaper.AK_AkJson_Map_Set(arg_map, "controlValue", reaper.AK_AkVariant_Double(auxValue))
            arg_bus = reaper.AK_AkJson_Array()        
            reaper.AK_AkJson_Array_Add(arg_bus,arg_map)
            reaper.AK_AkJson_Map_Set(arg, "auxSendValues", arg_bus)
            reaper.AK_Waapi_Call("ak.soundengine.setGameObjectAuxSendValues", arg, reaper.AK_AkJson_Map())
        end

    elseif api_call:find("SetState") then
        reaper.AK_AkJson_Map_Set(arg, "stateGroup", reaper.AK_AkVariant_String(object_name))
        reaper.AK_AkJson_Map_Set(arg, "state", switch)
        reaper.AK_Waapi_Call("ak.soundengine.setState", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("ExecuteActionOnEvent") then
        action, curve, duration = extract_action(api_call)
        -- reaper.ShowConsoleMsg("\naction: "..action.."\ncurve: "..curve.."\nduration: "..duration)
        reaper.AK_AkJson_Map_Set(arg, "actionType", reaper.AK_AkVariant_Int(action))
        reaper.AK_AkJson_Map_Set(arg, "transitionDuration", reaper.AK_AkVariant_Int(duration))
        reaper.AK_AkJson_Map_Set(arg, "fadeCurve", reaper.AK_AkVariant_Int(curve))
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_AkJson_Map_Set(arg, "event", reaper.AK_AkVariant_String(object_name))
        reaper.AK_Waapi_Call("ak.soundengine.executeActionOnEvent", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("SetRTPCValue") then
        reaper.AK_AkJson_Map_Set(arg, "rtpc", reaper.AK_AkVariant_String(object_name))
        reaper.AK_AkJson_Map_Set(arg, "value", rtpc)
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_Waapi_Call("ak.soundengine.setRTPCValue", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("UnregisterGameObj") then
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_Waapi_Call("ak.soundengine.unregisterGameObj", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("StopAll") then
        reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(gameObject_id))
        reaper.AK_Waapi_Call("ak.soundengine.stopAll", arg, reaper.AK_AkJson_Map())

    elseif api_call:find("StopPlayingID") then
        reaper.AK_AkJson_Map_Set(arg, "playingId", reaper.AK_AkVariant_Int(object_id))
        reaper.AK_AkJson_Map_Set(arg, "transitionDuration", reaper.AK_AkVariant_Int(100))
        reaper.AK_AkJson_Map_Set(arg, "fadeCurve", reaper.AK_AkVariant_Int(4))
        reaper.AK_Waapi_Call("ak.soundengine.stopPlayingID", arg, reaper.AK_AkJson_Map())
    else
        print("Unknown API call: " .. api_call)
    end
end

function extract_action(description)
    -- Define the mapping for Action To Execute
    local actionMap = {
        Stop = 0,
        Pause = 1,
        Break = 2,
        ReleaseEnvelope = 3
    }
    local curveMap = {
        Linear = 4,
        Log3 = 0
    }

    -- Extract values using pattern matching
    local action, fadeCurve, transitionDuration = description:match(
        "ExecuteActionOnEvent: Action To Execute: (%w+), Fade Curve: (%w+), Transition Duration: (%d+:%d+%.%d+)"
    )

    -- Convert extracted values
    local actionValue = actionMap[action] or -1 -- Return -1 for unknown actions
    local fadeCurveValue = curveMap[fadeCurve] or -1-- Fade Curve is always 4
    local transitionValue = 1000
    if transitionDuration ~= nil then
        local minutes, seconds, milliseconds = transitionDuration:match("(%d+):(%d+)%.(%d+)")
        transitionValue = (tonumber(minutes) * 60 * 1000) + (tonumber(seconds) * 1000) + tonumber(milliseconds)
    end
    return actionValue, fadeCurveValue, transitionValue
end

function extract_listeners(description)
    if string.find(description, "SetDefaultListeners:") == nil then
        return ""
    end
    local listeners = {}
    -- Use pattern matching to find the listeners
    local pattern = "SetDefaultListeners:%s*%[(.-)%]"
    local matched = description:match(pattern)
    if matched then
        for listener in matched:gmatch("[^,]+") do
            table.insert(listeners, listener:match("^%s*(.-)%s*$"))  -- Trim whitespace
        end
    else
        -- Handle single listener case without brackets
        matched = description:match("SetDefaultListeners:%s*(%S+)")
        if matched ~= nil then
            table.insert(listeners, matched:match("^%s*(.-)%s*$"))
        end
    end
    return listeners
end
-- Function to extract scaling factor
function extract_scaling_factor(description)
    local match = description:match("Scale factor:%s*(%w+)")
    return match and tonumber(match) or 0.0
end

-- Function to extract switch
function extract_switch(description)
    if string.find(description, "SetSwitch: ") == nil and string.find(description, "SetState: ") == nil then
        return ""
    end
    local match = string.match(description, "%S+$")
    if match:sub(1, 1) == '(' and match:sub(-1) == ')' then
        match = match:sub(2, -2)
        numValue = tonumber(match)
        if numValue then
            return numValue
        end
        return match or ""
    end
    return match or ""
end

-- Function to extract RTPC value
function extract_rtpc_value(description)
    local match = description:match("Value:%s*Value:%s*(%w+)")
    return match and tonumber(match) or 0.0
end

function extract_aux_send(description)
    local trimmedStr = description:gsub("SetGameObjectAuxSend : ", "")
    
    local auxBusName, value = trimmedStr:match("^(.-): (.+)$")
    if auxBusName == nil or value == nil then  
        return "(Unknown aux bus)", 0.0
    end
    return auxBusName, value
end


local function safe_tonumber(value)
    local num = tonumber(value)
    return num or 1.00
end

function extract_position_data(description)
    if string.find(description, "SetPosition: Position:") == nil then
        return reaper.AK_AkJson_Map()
    end
    -- Create AK Json Map for position data
    local position_data = reaper.AK_AkJson_Map()
    local front_data = reaper.AK_AkJson_Map()
    local top_data = reaper.AK_AkJson_Map()
    
    -- Use pattern matching to extract values
    local positionX, positionY, positionZ = description:match("Position:%(X:([-]?%d+%.?%d*[eE]?[-]?%d*),Y:([-]?%d+%.?%d*[eE]?[-]?%d*),Z:([-]?%d+%.?%d*[eE]?[-]?%d*)%)")
    local frontX, frontY, frontZ = description:match("Front:%(X:([-]?%d+%.?%d*[eE]?[-]?%d*),Y:([-]?%d+%.?%d*[eE]?[-]?%d*),Z:([-]?%d+%.?%d*[eE]?[-]?%d*)%)")
    local topX, topY, topZ = description:match("Top:%(X:([-]?%d+%.?%d*[eE]?[-]?%d*),Y:([-]?%d+%.?%d*[eE]?[-]?%d*),Z:([-]?%d+%.?%d*[eE]?[-]?%d*)%)")
    -- if frontZ == nil then
    --     reaper.ShowConsoleMsg("not found "..description)
    --     reaper.ShowConsoleMsg("\n")
    -- else
    --     reaper.ShowConsoleMsg("Position: (" .. positionX .. ", " .. positionY .. ", " .. positionZ .. ")\nFront: (" .. frontX .. ", " .. frontY .. ", " .. frontZ .. ")\nTop: (" .. topX .. ", " .. topY .. ", " .. topZ .. ")\n")
    --     reaper.ShowConsoleMsg("\n")
    -- end
    -- Setting values for position
    reaper.AK_AkJson_Map_Set(position_data, "x", reaper.AK_AkVariant_Double(safe_tonumber(positionX)))
    reaper.AK_AkJson_Map_Set(position_data, "y", reaper.AK_AkVariant_Double(safe_tonumber(positionY)))
    reaper.AK_AkJson_Map_Set(position_data, "z", reaper.AK_AkVariant_Double(safe_tonumber(positionZ)))

    -- Setting values for orientationFront
    reaper.AK_AkJson_Map_Set(front_data, "x", reaper.AK_AkVariant_Double(safe_tonumber(frontX)))
    reaper.AK_AkJson_Map_Set(front_data, "y", reaper.AK_AkVariant_Double(safe_tonumber(frontY)))
    reaper.AK_AkJson_Map_Set(front_data, "z", reaper.AK_AkVariant_Double(safe_tonumber(frontZ)))

    -- Setting values for orientationTop
    reaper.AK_AkJson_Map_Set(top_data, "x", reaper.AK_AkVariant_Double(safe_tonumber(topX)))
    reaper.AK_AkJson_Map_Set(top_data, "y", reaper.AK_AkVariant_Double(safe_tonumber(topY)))
    reaper.AK_AkJson_Map_Set(top_data, "z", reaper.AK_AkVariant_Double(safe_tonumber(topZ)))

    -- Create the final map to hold everything
    local final_data = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(final_data, "position", position_data)
    reaper.AK_AkJson_Map_Set(final_data, "orientationFront", front_data)
    reaper.AK_AkJson_Map_Set(final_data, "orientationTop", top_data)
    return final_data
end

function count_occurrences(input_string, substring)
    local count = 0
    for _ in string.gmatch(input_string, substring) do
        count = count + 1
    end
    return count
end


function PlaySoundWhenItemStart() 
    local eventsByTimestamp = {}

    for i = 0, reaper.CountTracks(rproj) - 1 do
        local track = reaper.GetTrack(rproj, i)
        local q, trackName = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
        
        if string.find(trackName, wwiseTrackName) and reaper.GetMediaTrackInfo_Value(track, "B_MUTE") ~= 1 then
            local numItems = reaper.CountTrackMediaItems(track)
            for j = 0, numItems - 1 do
                local mediaItem = reaper.GetTrackMediaItem(track, j)
                local itemStart = reaper.GetMediaItemInfo_Value(mediaItem, "D_POSITION")
                local itemEnd = itemStart + reaper.GetMediaItemInfo_Value(mediaItem, "D_LENGTH")
                local event
                local key = tostring(i) .. tostring(j)

                if playPosition >= itemStart and playPosition <= itemEnd then
                    a, event = reaper.GetSetMediaItemInfo_String(mediaItem, "P_NOTES", "", false)
                    if not TableContains(playingIDs, key) then
                        if count_occurrences(event, "#") >= 2 then
                            addToTable(playingIDs, key)
                            process_event_2D(event)
                        else
                            eventInfo = parseTable(event)
                            local timestamp = eventInfo.Timestamp

                            -- Group events by timestamp
                            if not eventsByTimestamp[timestamp] then
                                eventsByTimestamp[timestamp] = {}
                            end
                            table.insert(eventsByTimestamp[timestamp], eventInfo)
                            
                            addToTable(playingIDs, key)
                        end
                    end
                end

                if playPosition >= itemEnd or playPosition <= itemStart then
                    removeFromTable(playingIDs, key)
                end
            end
        end
    end

    -- Execute events in order of timestamp and then by order
    for timestamp, eventInfos in pairs(eventsByTimestamp) do
        -- Sort events by Order
        table.sort(eventInfos, function(a, b) 
            a_order = a.Order or 1
            b_order = b.Order or 1
            return tonumber(a_order) < tonumber(b_order)
        end)

        -- Execute sorted events
        for _, eventInfo in ipairs(eventInfos) do
            execute_api_from_log(eventInfo)
        end
    end
end

function UpdataPlayPosition()
    if isConnected then
        isPlaying = reaper.GetPlayState()
        if isPlaying == 1 then
            isStop = false
            playPosition = reaper.GetPlayPosition()
            PlaySoundWhenItemStart()
        elseif isPlaying == 0 and isStop == false then
            -- for name, id in pairs(registeredObj) do
            -- end
            local arg = reaper.AK_AkJson_Map()
            reaper.AK_AkJson_Map_Set(arg, "gameObject", reaper.AK_AkVariant_Int(0))
            reaper.AK_AkJson_Map_Set(arg, "event", reaper.AK_AkVariant_String("Stop_all"))
            reaper.AK_Waapi_Call("ak.soundengine.postEvent", arg, reaper.AK_AkJson_Map())

            isStop = true
            playingIDs = {}
        else
            playPosition = reaper.GetCursorPosition()
        end
        reaper.runloop(UpdataPlayPosition)
    end
end


connect()
buildNZDictionary()
-- Register game objects
local listenerArg = reaper.AK_AkJson_Map()
reaper.AK_AkJson_Map_Set(listenerArg, "gameObject", reaper.AK_AkVariant_Int(22334))
reaper.AK_AkJson_Map_Set(listenerArg, "name", reaper.AK_AkVariant_String("ReaperPlayer"))
reaper.AK_Waapi_Call("ak.soundengine.registerGameObj", listenerArg, reaper.AK_AkJson_Map())

execute_api_from_log(RegisterDefaultListener)
execute_api_from_log(SetDefaultListener)
reaper.runloop(UpdataPlayPosition)


