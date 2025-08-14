-- Author: moonpika
-- Contact: 1160654137@qq.com
-- vx: moonpikaz

local scriptPath = debug.getinfo(1, "S").source:match("@?(.*[\\/])")
local exportWavPath = "C:\\Users\\Administrator\\Desktop\\tools\\quickReaWwise"
local parentTypes = {"ActorMixer", "WorkUnit", "RandomSequenceContainer", "SwitchContainer", "BlendContainer", "Folder"}
local exportTargets = {}
local freeExportTargets = {}
local tempSingleExportName = "tempSingleExport"

-- Checks for duplicates in a list
local function containsDuplicates(list)
    local seen = {}
    for _, value in ipairs(list) do
        if seen[value] then return true end
        seen[value] = true
    end
    return false
end

-- Generates a random alphanumeric string
local function generateRandomString(length)
    math.randomseed(os.time())
    local chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    local result = ''
    
    for i = 1, length do
        local index = math.random(1, #chars)
        result = result .. chars:sub(index, index)
    end
    
    return result
end

-- Deletes .wav files in a specified directory
local function deleteWavFiles(directory)
    for file in io.popen('dir "' .. directory .. '" /b'):lines() do
        if file:match("%.wav$") then
            os.remove(directory .. "/" .. file)
        end
    end
end

-- Displays option dialog for user selection
local function showOptionsDialog(options)
    local instruction = #options == 0 and "--------当前无可操作选项-------使用说明:\n\n1.Reaper: 创建TimeSelection, 或选中单个音频块\n\n2.Wwise: 选中一个或多个要覆盖的声音, 或选中可以导入声音的地方\n\n3.如何选择Region: 用TimeSelection选中要导出的region, 批量导出时, 所有region必须命名" or "请选择一个选项:"
    gfx.init("快速导入Wwise工具", 600, 220)
    
    local selectedOption, addNewSource, lastMouseState = nil, false, 0
    
    -- Function to draw the dialog
    local function drawDialog()
        gfx.setfont(1, "Arial", 16)
        gfx.drawstr(instruction)

        for i, option in ipairs(options) do
            local isHovered = gfx.mouse_y > 40 + i * 30 and gfx.mouse_y < 40 + (i + 1) * 30
            gfx.x, gfx.y = 40, 40 + i * 30
            if isHovered then
                gfx.set(0.8, 0.8, 0.8)
                gfx.rect(30, 40 + i * 30, 10, 15, true)
            end
            gfx.set(1, 1, 1)
            gfx.drawstr(option)
            if gfx.mouse_cap & 1 == 1 and isHovered then
                selectedOption = option
                reaper.ShowConsoleMsg("\n正在执行:\n " .. selectedOption)
                gfx.quit()
                finalImportAction(selectedOption, addNewSource)
                return selectedOption
            end
        end

        -- Draw checkbox
        gfx.x, gfx.y = gfx.w - 150 + 20, gfx.h - 40
        gfx.drawstr("添加新Source")
        gfx.rect(gfx.w - 150, gfx.h - 40, 15, 15, false)
        if gfx.mouse_cap & 1 == 1 and lastMouseState == 0 and gfx.mouse_x > gfx.w - 150 and gfx.mouse_y > gfx.h - 40 and gfx.mouse_y < gfx.h - 25 then
            addNewSource = not addNewSource
        end
        if addNewSource then gfx.rect(gfx.w - 150 + 3, gfx.h - 40 + 3, 9, 9, true) end
        lastMouseState = gfx.mouse_cap & 1
    end

    -- Main loop function
    local function main()
        gfx.clear = 3355443
        drawDialog()
        if gfx.getchar() >= 0 then reaper.defer(main) else gfx.quit() end
    end

    main()
end

-- Exports selected media item to wav
local function ExportSelectedItemToWav(wavFilePath)
    local selected_item = reaper.GetSelectedMediaItem(0, 0)
    if not selected_item then reaper.ReaScriptError("请选中一个音频块后再试") return false end

    local item_pos = reaper.GetMediaItemInfo_Value(selected_item, "D_POSITION")
    local item_len = reaper.GetMediaItemInfo_Value(selected_item, "D_LENGTH")
    local orig_start, orig_end = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)

    reaper.GetSet_LoopTimeRange(true, false, item_pos, item_pos + item_len, false)
    
    local directory, file_name = wavFilePath:match("(.+)[\\/]"), wavFilePath:match("([^\\/]+)$")
    
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 64, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "WAV", true)
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 4, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", directory, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true)

    os.remove(wavFilePath)
    reaper.Main_OnCommand(42230, 0)
    reaper.GetSet_LoopTimeRange(true, false, orig_start, orig_end, false)
end

-- Exports time selection to wav
local function ExportTimeSelectionToWav(wavFilePath)
    local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    if timeSelStart == timeSelEnd then reaper.ReaScriptError("当前工程没有TimeSelection") return false end

    local directory, file_name = wavFilePath:match("(.+)[\\/]"), wavFilePath:match("([^\\/]+)$")
    
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "WAV", true)
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", directory, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true)

    os.remove(wavFilePath)
    reaper.Main_OnCommand(42230, 0)
end

-- Exports regions within time selection
local function ExportRegionsWithinTimeSelection(folderPath, matchWwiseSelections, specialAction)
    local exportedFilePaths = {}
    local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    if specialAction == "2" then 
        local mediaItemWavPath = folderPath.."\\"..tempSingleExportName..".wav"
        ExportSelectedItemToWav(mediaItemWavPath)
        table.insert(exportedFilePaths, mediaItemWavPath)
    elseif specialAction == "3" then
        local timeSelectionWavPath = folderPath .. "\\" .. tempSingleExportName..".wav"
        ExportTimeSelectionToWav(timeSelectionWavPath)
        table.insert(exportedFilePaths, timeSelectionWavPath)
    else
        local numMarkers = reaper.CountProjectMarkers(0)
        local validRegions = {}
        
        for i = 0, numMarkers - 1 do
            local retval, isRegion, regionStart, regionEnd, regionName = reaper.EnumProjectMarkers(i)
            if isRegion and regionStart >= timeSelStart and regionEnd <= timeSelEnd then
                if isValidRegionName(regionName) then
                    table.insert(validRegions, {name = regionName, start = regionStart, rend = regionEnd})
                else
                    reaper.ReaScriptError("包含不合法的region命名")
                    return false
                end
            end
        end
        
        for _, region in ipairs(validRegions) do
            local file_name = region.name .. ".wav"
            reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
            reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "WAV", true)
            reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
            reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
            reaper.GetSetProjectInfo_String(0, "RENDER_FILE", folderPath, true)
            reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", file_name, true)
            reaper.GetSet_LoopTimeRange(true, false, region.start, region.rend, false)
            local wavFilePath = folderPath .. "\\" .. file_name
            os.remove(wavFilePath)
            reaper.Main_OnCommand(42230, 0)
            table.insert(exportedFilePaths, wavFilePath)
        end
    end
    reaper.GetSet_LoopTimeRange(true, false, timeSelStart, timeSelEnd, false)
    return exportedFilePaths
end

-- Gets region names within time selection
local function GetRegionNamesWithinTimeSelection()
    local timeSelStart, timeSelEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    if timeSelStart == timeSelEnd then return false, {} end

    local regionNames = {}
    for i = 0, reaper.CountProjectMarkers(0) - 1 do
        local retval, isRegion, regionStart, regionEnd, regionName = reaper.EnumProjectMarkers(i)
        if isRegion and regionStart >= timeSelStart and regionEnd <= timeSelEnd and isValidRegionName(regionName) then
            table.insert(regionNames, regionName)
        end
    end
    return true, regionNames
end

-- Connects to WAAPI
local function connect()
    local startTime = os.time()
    while true do
        if reaper.AK_Waapi_Connect("localhost", 8080) then return true end
        if os.difftime(os.time(), startTime) >= 3 then
            reaper.ReaScriptError("链接Wwise超时,请确保Wwise已打开且端口未被占用")
            return false
        end
    end
end

-- Disconnects from WAAPI
local function disconnect()
    reaper.AK_Waapi_Disconnect()
end

-- Main execution
connect()
local allSounds = getAllSound()
local selections = getSelectedObjectInfo()
local hasRegion, regionNames = GetRegionNamesWithinTimeSelection()
if containsDuplicates(regionNames) then
    reaper.ShowMessageBox("注意: 你所选的regions包含重名, 无法批量导出", "error", 0)
end

local selection, countMatch, invalidSelection = "nil", 0, false
for _, item in ipairs(selections) do
    if isInList(item.type, parentTypes) then
        selection = item
    elseif item.type == "Sound" then
        table.insert(exportTargets, item.name)
        if hasRegion and isInList(item.name, regionNames) then
            countMatch = countMatch + 1
        end
    else
        invalidSelection = true
    end
end

local options = {}
if not invalidSelection then
    if selection == "$soundCollection" then
        if #selections == 1 then
            if #regionNames == 1 then
                table.insert(options, "1.所选region覆盖Wwise中选定的: "..selections[1].name)
            end
            if reaper.GetSelectedMediaItem(0, 0) then
                table.insert(options, "2.所选音频块覆盖Wwise中选定的: "..selections[1].name)
            end
            if reaper.GetSet_LoopTimeRange(false, false, 0, 0, false) then
                table.insert(options, "3.TimeSelection覆盖Wwise中选定的: "..selections[1].name)
            end
        else
            if hasRegion and countMatch > 0 then
                table.insert(options, "1.覆盖"..countMatch.."/"..#selections.."个Wwise中选定的声音")
            end
        end
    end
    if isParentType and hasRegion then
        table.insert(options, "4.导入"..#regionNames.."个声音到: "..selection.name)
    end
end

if not invalidSelection and countMatch > 0 then
    table.insert(options, "5.自动覆盖Wwise中"..countMatch.."个同名声音")
end

function finalImportAction(action, addNewSource)
    -- Implementation of final import action...
end

showOptionsDialog(options)