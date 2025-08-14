-- author: moonpika
-- contact: 1160654137@qq.com
-- vx: moonpikaz
local scriptPath = debug.getinfo(1, "S").source:match("@?(.*[\\/])")
local tempExportPath = scriptPath
local exportWavPath = "nil"

function generateRandomString(length)
    math.randomseed(os.time())
    local chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    local result = ''
    
    for i = 1, length do
        local index = math.random(1, #chars)
        result = result .. chars:sub(index, index)
    end
    
    return result
end

function ExportSelectedItemToWav(wavFilePath)
    -- Check if a media item is selected
    local selected_item = reaper.GetSelectedMediaItem(0, 0)
    if not selected_item then
        reaper.ReaScriptError("!请选中一个音频块后再试")
        return false
    end
    
    -- Get item properties
    local item_pos = reaper.GetMediaItemInfo_Value(selected_item, "D_POSITION")
    local item_len = reaper.GetMediaItemInfo_Value(selected_item, "D_LENGTH")
    
    -- Save current time selection
    local orig_start, orig_end = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    
    -- Set time selection to item bounds
    reaper.GetSet_LoopTimeRange(true, false, item_pos, item_pos + item_len, false)

    -- Extract the directory and file name from the provided path
    local directory = wavFilePath:match("(.+)[\\/]") -- This extracts the directory path
    local file_name = wavFilePath:match("([^\\/]+)$") -- This gets the last part of the path (the file name)
    
    -- Set render settings
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 64, true) -- via master
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "WAV", true) -- WAV 
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true) -- Sample rate 44100
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 4, true) -- media item
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", directory, true) -- Set to folder path
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true) -- Use extracted file name

    
    -- Run the render command (ID 42230 is "Render project to disk...")
    reaper.Main_OnCommand(42230, 0)
    
    -- Restore original time selection
    reaper.GetSet_LoopTimeRange(true, false, orig_start, orig_end, false)
end



-- Function to connect to WAAPI
function connect()
    local startTime = os.time()
    local isConnected = false
    while true do
        isConnected = reaper.AK_Waapi_Connect("localhost", 8080)
        if isConnected then
            break
        end
        if os.difftime(os.time(), startTime) >= 3 then
            reaper.ReaScriptError("!链接Wwise超时,请确保Wwise已打开且端口未被占用")
            return false
        end
    end
    return true
end

-- Function to disconnect from WAAPI
function disconnect()
    reaper.AK_Waapi_Disconnect()
    isConnected = false
    -- reaper.ShowConsoleMsg("Disconnected from WAAPI.\n")
end

function addSoundTag(originalString)
    local lastBackslashIndex = originalString:match(".*()\\")
    if lastBackslashIndex then
        -- Construct the new string with "<Sound SFX>" appended
        local modifiedString = originalString:sub(1, lastBackslashIndex) .. "<Sound SFX>" .. originalString:sub(lastBackslashIndex + 1)
        return modifiedString
    else
        return originalString -- Return the original string if no backslash is found
    end
end

connect()
options = reaper.AK_AkJson_Map()
optionArray = reaper.AK_AkJson_Array()        
reaper.AK_AkJson_Array_Add(optionArray,reaper.AK_AkVariant_String("id"))
reaper.AK_AkJson_Array_Add(optionArray,reaper.AK_AkVariant_String("originalFilePath"))
reaper.AK_AkJson_Array_Add(optionArray,reaper.AK_AkVariant_String("path"))
reaper.AK_AkJson_Array_Add(optionArray,reaper.AK_AkVariant_String("name"))
reaper.AK_AkJson_Map_Set(options, "return", optionArray)
result = reaper.AK_Waapi_Call("ak.wwise.ui.getSelectedObjects", reaper.AK_AkJson_Map(), options)
local status = reaper.AK_AkJson_GetStatus(result)
local id = "nil"
local path = "nil"
local wavPath = "nil"
local soundName = "nil.wav"
if(status) then
    local objects = reaper.AK_AkJson_Map_Get(result, "objects")
    local item = reaper.AK_AkJson_Array_Get(objects, 0)
    local akid = reaper.AK_AkJson_Map_Get(item, "id")
    local akpath = reaper.AK_AkJson_Map_Get(item, "path")
    local akwavPath = reaper.AK_AkJson_Map_Get(item, "originalFilePath")
    local akname = reaper.AK_AkJson_Map_Get(item, "name")
    id = reaper.AK_AkVariant_GetString(akid)
    path = reaper.AK_AkVariant_GetString(akpath)
    path = addSoundTag(path)
    wavPath = reaper.AK_AkVariant_GetString(akwavPath)
    soundName = reaper.AK_AkVariant_GetString(akname)
end

local file_name = wavPath:match("([^\\/]+)$") -- This gets the last part of the path (the file name)
if not tempExportPath:match("[\\/].*$") then
    tempExportPath = tempExportPath .. "/"
end

exportWavPath = tempExportPath..soundName..".wav"
if file_name ~= nil then
    exportWavPath = tempExportPath.."temp_"..generateRandomString(3).."_"..file_name
end
-- reaper.ShowConsoleMsg(exportWavPath)



ExportSelectedItemToWav(exportWavPath)

ImportArg = reaper.AK_AkJson_Map()
Defualt = reaper.AK_AkJson_Map()
Items = reaper.AK_AkJson_Array()
Item = reaper.AK_AkJson_Map()
reaper.AK_AkJson_Map_Set(Item, "audioFile", reaper.AK_AkVariant_String(exportWavPath))
reaper.AK_AkJson_Map_Set(Item, "objectPath", reaper.AK_AkVariant_String(path))
local subPath = wavPath:match("SFX\\(.+)\\.+%.wav$")
if subPath ~= nil then
    reaper.AK_AkJson_Map_Set(Item, "originalsSubFolder", reaper.AK_AkVariant_String(subPath))
end
reaper.AK_AkJson_Array_Add(Items,Item)
reaper.AK_AkJson_Map_Set(ImportArg, "importOperation", reaper.AK_AkVariant_String("useExisting"))
reaper.AK_AkJson_Map_Set(Defualt, "importLanguage", reaper.AK_AkVariant_String("SFX"))
reaper.AK_AkJson_Map_Set(ImportArg, "default", Defualt)
reaper.AK_AkJson_Map_Set(ImportArg, "imports", Items)

reaper.AK_Waapi_Call("ak.wwise.core.audio.import", ImportArg, reaper.AK_AkJson_Map())
-- reaper.ShowConsoleMsg("\ndone")
disconnect()


os.remove(exportWavPath)