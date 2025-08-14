local NZDictionary = {}
local isConnected = false

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

function process_event(event)
    -- Check if the event is in the NZDictionary
    if NZDictionary[event] then
        event = NZDictionary[event]
    end

    -- Register game objects and post event
    local listenerArg = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(listenerArg, "gameObject", reaper.AK_AkVariant_Int(2233445))
    reaper.AK_AkJson_Map_Set(listenerArg, "name", reaper.AK_AkVariant_String("QuickListener"))
    reaper.AK_Waapi_Call("ak.soundengine.registerGameObj", listenerArg, reaper.AK_AkJson_Map())

    local playArg = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(playArg, "gameObject", reaper.AK_AkVariant_Int(1122334))
    reaper.AK_AkJson_Map_Set(playArg, "event", reaper.AK_AkVariant_String(event))
    reaper.AK_Waapi_Call("ak.soundengine.postEvent", playArg, reaper.AK_AkJson_Map())
end

-- Example usage
if connect() then
    buildNZDictionary()
    process_event("1883")
    disconnect()  -- Disconnect after the operations
end