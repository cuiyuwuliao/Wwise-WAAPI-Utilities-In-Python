-- author: moonpika
-- contact: 1160654137@qq.com
-- vx: moonpikaz
local scriptPath = debug.getinfo(1, "S").source:match("@?(.*[\\/])")
local tempExportPath = scriptPath
local exportWavPath = "C:\\Users\\Administrator\\Desktop\\tools\\quickReaWwise"
local parentTypes = {"ActorMixer", "WorkUnit", "RandomSequenceContainer", "SwitchContainer", "BlendContainer", "Folder"}
local exportTargets = {}
local freeExportTargets = {}
local tempSingleExportName = "tempSingleExport"

function containsDuplicates(list)
    local seen = {}  -- Table to keep track of seen elements
    for _, value in ipairs(list) do
        if seen[value] then
            return true  -- Duplicate found
        end
        seen[value] = true  -- Mark this value as seen
    end
    return false  -- No duplicates found
end


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

function deleteWavFiles(directory)
    local files = {}
    for file in io.popen('dir "' .. directory .. '" /b'):lines() do
        if file:match("%.wav$") then
            table.insert(files, file)
        end
    end
    
    if #files == 0 then
        return -- Do nothing if no .wav files found
    end

    for _, file in ipairs(files) do
        os.remove(directory .. "/" .. file) -- Use the appropriate path separator
    end
end

function showOptionsDialog(options)
    -- Initialize the graphics window
    local instruction = "请选择一个选项:"
    if #options == 0 then
        instruction = "--------当前无可操作选项-------使用说明:\n\n1.Reaper: 创建TimeSelection, 或选中单个音频块\n\n2.Wwise: 选中一个或多个要覆盖的声音, 或选中可以导入声音的地方\n\n3.如何选择Region: 用TimeSlection选中要导出的region, 批量导出时, 所有region必须命名"
    end

    gfx.init(" ( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°).快速导入Wwise工具 ( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°).", 600, 220)
    
    local selectedOption = nil
    local addNewSource = false -- Initial state of the checkbox
    local lastMouseState = 0
    
    -- Function to draw the dialog
    local function drawDialog()
        gfx.setfont(1, "Arial", 16)
        gfx.x = 20
        gfx.y = 20
        gfx.drawstr(instruction)
        
        -- Draw options
        for i, option in ipairs(options) do
            gfx.x = 40
            gfx.y = 40 + i * 30
            -- Check if the option is hovered
            local isHovered = gfx.mouse_y > 40 + i * 30 and gfx.mouse_y < 40 + (i + 1) * 30
            -- Draw a box behind the option if hovered
            if isHovered then
                gfx.set(0.8, 0.8, 0.8) -- Set color for the box (light gray)
                gfx.rect(30, 40 + i * 30, 10, 15, true) -- Draw filled rectangle
            end
            gfx.set(1, 1, 1) -- Set text color (white)
            gfx.drawstr(option)
            -- Check if the option is clicked
            if gfx.mouse_cap & 1 == 1 and isHovered then
                selectedOption = option
                reaper.ShowConsoleMsg("\n正在执行:\n " .. selectedOption)
                gfx.quit() -- Close the dialog
                finalImportAction(selectedOption, addNewSource)
                return selectedOption
            end
        end
                
        -- Draw checkbox
        local checkboxX = gfx.w - 150
        local checkboxY = gfx.h - 40
        gfx.x = checkboxX + 20
        gfx.y = checkboxY
        gfx.drawstr("添加新Source")
        
        -- Draw checkbox square
        gfx.rect(checkboxX, checkboxY, 15, 15, false)
        
        -- Check if the checkbox is clicked
        if gfx.mouse_cap & 1 == 1 and lastMouseState == 0 and gfx.mouse_x > checkboxX and gfx.mouse_x < checkboxX + 15 and gfx.mouse_y > checkboxY and gfx.mouse_y < checkboxY + 15 then
            addNewSource = not addNewSource -- Toggle checkbox state
        end
        
        -- Fill checkbox if checked
        if addNewSource then
            gfx.rect(checkboxX + 3, checkboxY + 3, 9, 9, true)
        end
        lastMouseState = gfx.mouse_cap & 1
    end
    
    -- Main loop function
    local function main()
        gfx.clear = 3355443 -- Set background color
        drawDialog()
        
        if gfx.getchar() >= 0 then
            reaper.defer(main) -- Keep the window open
        else
            gfx.quit() -- Ensure the window is closed if getchar returns -1
            return "quit"
        end
    end
    
    -- Start the main loop
    main()
end


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

function isInList(element, list)
    for _, value in ipairs(list) do
        if value == element then
            return true
        end
    end
    return false
end

function ExportSelectedItemToWav(wavFilePath)
    -- Check if a media item is selected
    local selected_item = reaper.GetSelectedMediaItem(0, 0)
    if not selected_item then
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
    os.remove(wavFilePath)
    reaper.Main_OnCommand(42230, 0)
    -- Restore original time selection
    reaper.GetSet_LoopTimeRange(true, false, orig_start, orig_end, false)
end


function ExportTimeSelectionToWav(wavFilePath)
    -- Get the current time selection
    local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    -- Check if there is a valid time selection
    if timeSelStart == timeSelEnd then
        reaper.ReaScriptError("!当前工程没有TimeSelection")
        return false
    end
    -- Extract the directory and file name from the provided path
    local directory = wavFilePath:match("(.+)[\\/]") -- This extracts the directory path
    local file_name = wavFilePath:match("([^\\/]+)$") -- This gets the last part of the path (the file name)
    -- Set render settings
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true) -- via master
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "WAV", true) -- WAV
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true) -- Sample rate 44100
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true) -- time selection
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", directory, true) -- Set to folder path
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true) -- Use extracted file name
    -- Run the render command (ID 42230 is "Render project to disk...")
    os.remove(wavFilePath)
    reaper.Main_OnCommand(42230, 0)
end

-- specialAction: 1导出音频块, 2导出timeSelection
function ExportRegionsWithinTimeSelection(folderPath, matchWwiseSelections, specialAction)
    -- deleteWavFiles(folderPath) -- before exporting, clear the folder
    local exportedFilePaths = {}  -- List to store exported file paths
    -- Get the current time selection
    local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    -- Check if there is a valid time selection
    if specialAction == "2" then 
        local mediaItemWavPath = folderPath.."\\"..tempSingleExportName..".wav"
        ExportSelectedItemToWav(mediaItemWavPath)
        table.insert(exportedFilePaths, mediaItemWavPath)
    elseif specialAction == "3" then
        local timeSelectionWavPath = folderPath .. "\\" .. tempSingleExportName..".wav"
        ExportTimeSelectionToWav(timeSelectionWavPath)
        table.insert(exportedFilePaths, timeSelectionWavPath)
    else
        -- Get the number of project markers (regions)
        local numMarkers, numRegions = reaper.CountProjectMarkers(0)
        
        local validRegions = {}        -- List to store valid regions for export
        -- Function to check if the region name is valid
        local function isValidRegionName(name)
            return name and not name:match("^[%d]") and name:match("^[%a%d_]+$") -- Check for valid name
        end

        -- Iterate over all markers and regions to gather valid regions
        for i = 0, numMarkers - 1 do
            local retval, isRegion, regionStart, regionEnd, regionName, regionIndex = reaper.EnumProjectMarkers(i)
            if regionName:match("#(.-)#") then
                regionName = regionName:match("#(.-)#")
            end
            if regionName:sub(-4) == ".wav" then
                regionName = regionName:sub(1, -5) -- Remove the last 4 characters
            end
            reaper.ShowConsoleMsg(regionName)
            -- Check if the marker is a region and within the current time selection
            if isRegion and regionStart >= timeSelStart and regionEnd <= timeSelEnd then
                if specialAction == "5" then
                    exportTargets = freeExportTargets
                end
                if #exportTargets ~= 0 and not isInList(regionName, exportTargets) and matchWwiseSelections then
                    reaper.ShowConsoleMsg("\n跳过导出: "..regionName)
                    --如果指定了导出的音频，又不是导出的音频，啥都不做。!!!这个逻辑依赖于全局变量exportTargets!!!
                else
                    if regionName == "" and not matchWwiseSelections then
                        regionName = tempSingleExportName
                    end
                    if isValidRegionName(regionName) then
                        table.insert(validRegions, {name = regionName, start = regionStart, rend = regionEnd})
                    else
                        reaper.ReaScriptError("!包含不合法的region命名")
                        return false
                    end
                end
            end
        end
        -- Export valid regions
        for _, region in ipairs(validRegions) do
            local file_name = region.name .. ".wav" -- Use region name as file name
            -- Set render settings
            reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true) -- via master
            reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "WAV", true) -- WAV
            reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true) -- Sample rate 44100
            reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true) -- time selection
            reaper.GetSetProjectInfo_String(0, "RENDER_FILE", folderPath, true) -- Set to folder path
            reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true) -- Use extracted file name
            -- Set time selection to region bounds
            reaper.GetSet_LoopTimeRange(true, false, region.start, region.rend, false)
            wavFilePath = folderPath .. "\\" .. file_name
            os.remove(wavFilePath)
            reaper.Main_OnCommand(42230, 0)
            -- Add the exported file path to the list
            table.insert(exportedFilePaths, wavFilePath)
        end
    end
    -- Restore original time selection
    reaper.GetSet_LoopTimeRange(true, false, timeSelStart, timeSelEnd, false)
    return exportedFilePaths  -- Return the list of exported file paths
end


function GetRegionNamesWithinTimeSelection()
    -- Get the current time selection
    local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    -- Check if there is a valid time selection
    if timeSelStart == timeSelEnd then
        return false, {}
    end
    -- Get the number of project markers (regions)
    local numMarkers, numRegions = reaper.CountProjectMarkers(0)
    local regionNames = {}  -- List to store valid region names
    -- Function to check if the region name is valid
    local function isValidRegionName(name)
        return name and not name:match("^[%d]") and name:match("^[%a%d_]+$") -- Check for valid name
    end
    -- Iterate over all markers and regions to gather valid regions
    for i = 0, numMarkers - 1 do
        local retval, isRegion, regionStart, regionEnd, regionName, regionIndex = reaper.EnumProjectMarkers(i)
        
        if regionName:match("#(.-)#") then
            regionName = regionName:match("#(.-)#")
        end
        if regionName:sub(-4) == ".wav" then
            regionName = regionName:sub(1, -5) -- Remove the last 4 characters
        end
        -- Check if the marker is a region and within the current time selection
        if isRegion and regionStart >= timeSelStart and regionEnd <= timeSelEnd then
            if isValidRegionName(regionName) then
                table.insert(regionNames, regionName)
            else
                return false, {}
            end
        end
    end
    
    return true, regionNames
end

function UpdateRegionName(oldName, newName)
    -- Iterate through all regions
    local numRegions = reaper.CountProjectMarkers(0)
    for i = 0, numRegions - 1 do
        local retval, isRegion, regionStart, regionEnd, regionName, regionIndex = reaper.EnumProjectMarkers(i)
        if isRegion and regionName == oldName then
            -- Update the region name
            reaper.SetProjectMarker(regionIndex, true, regionStart, regionEnd, newName)
            return
        end
    end
    reaper.ShowMessageBox("Region with name '" .. oldName .. "' not found.", "Error", 0)
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

function getSelectedObjectInfo()
    local options = reaper.AK_AkJson_Map()
    local optionArray = reaper.AK_AkJson_Array()        
    reaper.AK_AkJson_Array_Add(optionArray, reaper.AK_AkVariant_String("id"))
    reaper.AK_AkJson_Array_Add(optionArray, reaper.AK_AkVariant_String("originalFilePath"))
    reaper.AK_AkJson_Array_Add(optionArray, reaper.AK_AkVariant_String("path"))
    reaper.AK_AkJson_Array_Add(optionArray, reaper.AK_AkVariant_String("name"))
    reaper.AK_AkJson_Array_Add(optionArray, reaper.AK_AkVariant_String("type"))
    reaper.AK_AkJson_Map_Set(options, "return", optionArray)
    local result = reaper.AK_Waapi_Call("ak.wwise.ui.getSelectedObjects", reaper.AK_AkJson_Map(), options)
    local status = reaper.AK_AkJson_GetStatus(result)

    local dataList = {}
    if status then
        local objects = reaper.AK_AkJson_Map_Get(result, "objects")
        local numObjects = reaper.AK_AkJson_Array_Size(objects)
        
        for i = 0, numObjects -1 do
            local objects = reaper.AK_AkJson_Map_Get(result, "objects")
            local data = {id = "nil",path = "nil",wavPath = "nil",soundName = "nil.wav",type = "nil"}
            local item = reaper.AK_AkJson_Array_Get(objects, i)
            local akid = reaper.AK_AkJson_Map_Get(item, "id")
            local akpath = reaper.AK_AkJson_Map_Get(item, "path")
            local akwavPath = reaper.AK_AkJson_Map_Get(item, "originalFilePath")
            local akname = reaper.AK_AkJson_Map_Get(item, "name")
            local aktype = reaper.AK_AkJson_Map_Get(item, "type")

            data.id = reaper.AK_AkVariant_GetString(akid)
            data.path = reaper.AK_AkVariant_GetString(akpath)
            data.wavPath = reaper.AK_AkVariant_GetString(akwavPath)
            data.name = reaper.AK_AkVariant_GetString(akname)
            data.type = reaper.AK_AkVariant_GetString(aktype)
            if data.type == "AudioFileSource" then --如果选中了source, 抢救一下, 信息变成sound, 注意ID不会变
                local alreadyAdded = false
                for _, ldata in ipairs(dataList) do
                    if ldata.name == data.name and ldata.type == "Sound" then
                        alreadyAdded = true
                    end
                end
                if not alreadyAdded then --已经有同名sound了就忽略
                    local soundPath, fileName = data.path:match("^(.*)\\(.*)$")
                    local folderPth, soundName = soundPath:match("^(.*)\\(.*)$")
                    data.path = folderPth
                    data.name = soundName
                    data.type = "Sound"
                end
            end
            table.insert(dataList, data)
        end
    end
    return dataList
end

function getAllSound()
    local allSounds = {}
    local args = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(args, "waql", reaper.AK_AkVariant_String("$ from type Sound"))

    local fieldsToReturn = reaper.AK_AkJson_Array()
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("id"))
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("notes"))
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("name"))
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("path"))
    reaper.AK_AkJson_Array_Add(fieldsToReturn, reaper.AK_AkVariant_String("originalFilePath"))

    local options = reaper.AK_AkJson_Map()
    reaper.AK_AkJson_Map_Set(options, "return", fieldsToReturn)

    local result = reaper.AK_Waapi_Call("ak.wwise.core.object.get", args, options)
    local status = reaper.AK_AkJson_GetStatus(result)

    if status then
        local objects = reaper.AK_AkJson_Map_Get(result, "return")
        local numObjects = reaper.AK_AkJson_Array_Size(objects)

        for i = 0, numObjects -1 do
            local object = reaper.AK_AkJson_Array_Get(objects, i)
            local objectId = reaper.AK_AkVariant_GetString(reaper.AK_AkJson_Map_Get(object, "id"))
            local objectNotes = reaper.AK_AkVariant_GetString(reaper.AK_AkJson_Map_Get(object, "notes"))
            local objectName = reaper.AK_AkVariant_GetString(reaper.AK_AkJson_Map_Get(object, "name"))
            local objectPath = reaper.AK_AkVariant_GetString(reaper.AK_AkJson_Map_Get(object, "path"))
            local objectWavPath = reaper.AK_AkVariant_GetString(reaper.AK_AkJson_Map_Get(object, "originalFilePath"))
            soundData = {
                id = objectId,
                notes = objectNotes,
                name = objectName,
                path = objectPath,
                wavPath = objectWavPath
            }
            table.insert(allSounds, soundData)
            
        end
        return allSounds
    else
        reaper.ShowConsoleMsg("Failed to retrieve Sounds.\n")
        return {}
    end
    reaper.ShowConsoleMsg("Got no return on Sounds\n")
    return {}
end

function wwiseImport(objects, useExisting)
    local ImportArg = reaper.AK_AkJson_Map()
    local Default = reaper.AK_AkJson_Map()
    local Items = reaper.AK_AkJson_Array()
    
    for _, object in ipairs(objects) do
        local Item = reaper.AK_AkJson_Map()
        -- Set audioFile and objectPath from the current object
        reaper.AK_AkJson_Map_Set(Item, "audioFile", reaper.AK_AkVariant_String(object.audioFile))
        reaper.AK_AkJson_Map_Set(Item, "objectPath", reaper.AK_AkVariant_String(addSoundTag(object.objectPath)))
        -- Handle the original subfolder extraction
        if object.subPath ~= nil then
            reaper.AK_AkJson_Map_Set(Item, "originalsSubFolder", reaper.AK_AkVariant_String(object.subPath))
        end
        -- Add the current Item to the Items array
        reaper.AK_AkJson_Array_Add(Items, Item)
    end
    -- Set the import operation
    local operation = useExisting and "useExisting" or "createNew"
    reaper.AK_AkJson_Map_Set(ImportArg, "importOperation", reaper.AK_AkVariant_String(operation))
    reaper.AK_AkJson_Map_Set(ImportArg, "autoAddToSourceControl", reaper.AK_AkVariant_Bool(true))
    -- Set default import language
    reaper.AK_AkJson_Map_Set(Default, "importLanguage", reaper.AK_AkVariant_String("SFX"))
    -- Set the defaults and imports in the ImportArg
    reaper.AK_AkJson_Map_Set(ImportArg, "default", Default)
    reaper.AK_AkJson_Map_Set(ImportArg, "imports", Items)
    -- Call the import function
    reaper.AK_Waapi_Call("ak.wwise.core.audio.import", ImportArg, reaper.AK_AkJson_Map())
    -- reaper.ShowConsoleMsg("\ndone")
end

function changeFileName(filePath, newFileName)
    local directory = filePath:match("^(.*[/\\])") or ""
    local newFilePath = directory .. newFileName .. (filePath:match("%.([^%.]+)$") and "." .. filePath:match("%.([^%.]+)$") or "")
    os.rename(filePath, newFilePath)
    return newFilePath
end

function RegionsCheck(regionNames, allSounds)
    -- Statistics for how many regions exist in Wwise
    local nonDistinctSounds = {}
    local index = 1
    local updates = {}  -- To store regions that will be updated
    local countMatch_allSounds = 0
    local freeExportTargets = {}
    local soundHasDupe = false

    for _, regionName in ipairs(regionNames) do
        local dupes = {}
        for _, soundData in ipairs(allSounds) do
            if regionName == soundData.name or regionName .. "_1P" == soundData.name or regionName .. "_1p" == soundData.name then
                -- Store the update information
                if regionName ~= soundData.name then
                    table.insert(updates, { oldName = regionName, newName = soundData.name })
                end
                table.insert(dupes, soundData)

                if #dupes < 2 then
                    countMatch_allSounds = countMatch_allSounds + 1
                    table.insert(freeExportTargets, regionName)
                end
            end
        end
        index = index + 1

        if #dupes > 1 then
            soundHasDupe = true
            nonDistinctSounds[regionName] = dupes
        end
    end

    -- Ask for confirmation to update all regions at once
    if #updates > 0 then
        local updateList = "检测到模糊匹配:\n"
        for _, update in ipairs(updates) do
            updateList = updateList .. "'" .. update.oldName .. "' to '" .. update.newName .. "'\n"
        end

        local userResponse = reaper.ShowMessageBox(
            updateList .. "是否要修改region命名来匹配wwise中的名称?",
            "模糊匹配",
            1 -- 1 for OK/Cancel
        )

        if userResponse == 1 then -- User clicked OK
            for _, update in ipairs(updates) do
                UpdateRegionName(update.oldName, update.newName)
                -- Update the regionNames table
                for i, name in ipairs(regionNames) do
                    if name == update.oldName then
                        regionNames[i] = update.newName
                    end
                end
            end
        end
    end
    return countMatch_allSounds, soundHasDupe, nonDistinctSounds
end


-- Main execution
connect()
local allSounds = getAllSound()
local selections = getSelectedObjectInfo()
local hasRegion, regionNames = GetRegionNamesWithinTimeSelection()
local duplictaeRegions = false
if containsDuplicates(regionNames) then
    reaper.ShowMessageBox("注意: 你所选的regions包含重名, 无法批量导出", "error", 0)
    duplictaeRegions = true
end



local selection = "nil"
local countMatch = 0 -- 所选的对象中匹配的
local nonDistinctSounds = {}
local countMatch_allSounds = 0 -- 所有wwise对象中匹配的
local soundHasDupe = false
local invalidSelection = false

for i = 1, #selections do
    local item = selections[i]
    if isInList(item.type, parentTypes) then
        selection = item
    elseif item.type == "Sound" then
        table.insert(exportTargets, item.name) --加入导入列表
        selection = "$soundCollection"
        if hasRegion then
            countMatch_allSounds, soundHasDupe, nonDistinctSounds = RegionsCheck(regionNames, allSounds)
            if isInList(item.name, regionNames) then
                countMatch = countMatch + 1
            end
        end
    else
        invalidSelection = true
    end
end






local isParentType = (selection ~= "$soundCollection" and selection ~= "nil")
options = {}
if not invalidSelection then
    if selection == "$soundCollection" then
        if #selections == 1 then
            if #regionNames == 1 then
                table.insert(options, "1.所选region覆盖Wwise中选定的: "..selections[1].name)
            end
            local selected_item = reaper.GetSelectedMediaItem(0, 0)
            if selected_item then
                table.insert(options, "2.所选音频块覆盖Wwise中选定的: "..selections[1].name)
            end
            local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
            -- Check if there is a valid time selection
            if timeSelStart ~= timeSelEnd then
                table.insert(options, "3.TimeSelection覆盖Wwise中选定的: "..selections[1].name)
            end
        else
            if hasRegion and countMatch ~= 0 then
                table.insert(options, "1.覆盖"..countMatch.."/"..#selections.."个Wwise中选定的声音")
            end
        end
    end

    if isParentType and hasRegion and not duplictaeRegions and #regionNames~= 0 then
        table.insert(options, "4.导入"..#regionNames.."个声音到: "..selection.name)
    end
end

if countMatch_allSounds > 0 and not duplictaeRegions then
    table.insert(options, "5.自动覆盖Wwise中"..countMatch_allSounds.."个同名声音 (Wwise不可有重复名字)")
end

function finalImportAction(action, addNewSource)
    local actionIndex = string.sub(action, 1, 1)
    if actionIndex == "5" and soundHasDupe then
        msg = "以下声音命名重复, 为避免误操作, 请重命名后再导入"
        for dupeName, dupes in pairs(nonDistinctSounds) do
            msg = msg .. "\n" .. "↓↓↓↓↓" .. dupeName .. "↓↓↓↓↓"
            for _, dupe in ipairs(dupes) do
                msg = msg .. "\n" .. dupe.path
            end
        end
        reaper.ShowMessageBox(msg, "error", 0)
        reaper.ReaScriptError("!请保证导出的名称在Wwise中不存在多个重名")
    end 
    local exportWwiseSelectionsOnly = true
    if (actionIndex == "1" or actionIndex == "2" or actionIndex == "3") and #selections == 1 then --如果wwise只选了一个对象来覆盖, 且只有一个region, 导入的文件以wwise选中的对象命名为准
        exportWwiseSelectionsOnly = false
    end
    reaper.ShowConsoleMsg("\n\n正在渲染...")
    local wavFiles = ExportRegionsWithinTimeSelection(exportWavPath, exportWwiseSelectionsOnly, actionIndex)
    local soundToImport = {}
    
    if not wavFiles then
        reaper.ReaScriptError("!文件导出不成功")
    end

    local filesToClear = {}
    for _, file in ipairs(wavFiles) do
        local soundName = ""
        local soundName = file:match("([^\\/]+)%.wav$") --不含.wav的声音名字
        if not exportWwiseSelectionsOnly then --一一对应的导出，以Wwise选中对象命名为准
            soundName = selections[1].name
            file = changeFileName(file, soundName)
            table.insert(filesToClear,file)
        end
        if not isParentType then --不是父级对象，直接覆盖导入声音, selection.path已经包含soundName,所以留空
            scope = selections
            if actionIndex == "5" then -- 选3时进行Wwise全局匹配, 而非匹配选中对象
                scope = allSounds
            end
            for _, item in ipairs(scope) do
                if item.name == soundName then
                    selection = item
                    soundName = ""
                end
            end
        else --是父级对象, 需要添加导入声音的名字, 2号选项全部会走这里
            soundName = "\\"..soundName
        end

        local subPath = selection.wavPath:match("SFX\\(.+)\\.+%.wav$")
        
        if subPath ~= nil then
            reaper.AK_AkJson_Map_Set(Item, "originalsSubFolder", reaper.AK_AkVariant_String(subPath))
        end
        local newFileName = "nil"
        if addNewSource then
            if soundName ~= "" then
                newFileName = soundName.."_"..generateRandomString(3)
            else
                newFileName = selection.name.."_"..generateRandomString(3)
            end
            file = changeFileName(file, newFileName)
            table.insert(filesToClear,file)
        elseif not exportWwiseSelectionsOnly then --覆盖当前选中的source, 如果希望覆盖和sound命名相同的source, 删除下面逻辑即可
            if soundName ~= "" then
                newFileName = soundName
            else
                newFileName = selection.name
            end
            local activeSourceName = selection.wavPath:match("([^\\/]+)%.wav$")
            if activeSourceName ~= nil then
                newFileName = activeSourceName
            end
            file = changeFileName(file, newFileName)
            table.insert(filesToClear,file)
        end
        
        local sound = {
            subPath = subPath,
            audioFile = file,
            objectPath = selection.path..soundName
        }
        table.insert(soundToImport, sound)
    end
    reaper.ShowConsoleMsg("\n\n正在导入Wwise...")
    if #soundToImport ~= 0 then
        wwiseImport(soundToImport, true)
    end
    for _, file in ipairs(wavFiles) do
        os.remove(file)
    end
    for _, file in ipairs(filesToClear) do
        os.remove(file)
    end
    disconnect()
    reaper.ShowConsoleMsg("\n\n导入结束")
end



showOptionsDialog(options)





