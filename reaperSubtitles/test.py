from reapy import reascript_api as RPR
import reapy
reapy.configure_reaper()

reapy.print("Hello world!")
# def find_items_with_notes_at_play_position():
#     # Initialize an empty list to store dictionaries of item index and notes
#     items_with_notes = []

#     # Get the current play position
#     play_position = RPR.GetPlayPosition()

#     # Get the number of items in the current project
#     num_items = RPR.CountMediaItems(0)  # 0 refers to the current project

#     # Iterate through each item in the project
#     for i in range(num_items):
#         # Get the media item at index i
#         media_item = RPR.GetMediaItem(0, i)

#         # Get the start and end position of the media item
#         item_start = RPR.GetMediaItemInfo_Value(media_item, "D_POSITION")
#         item_length = RPR.GetMediaItemInfo_Value(media_item, "D_LENGTH")
#         item_end = item_start + item_length

#         # Check if the play position is within the item's range
#         if item_start <= play_position <= item_end:
#             # Get the notes of the media item
#             retval, notes = RPR.GetSetMediaItemInfo_String(media_item, "P_NOTES", "", False)

#             # If notes are not empty, add the item index and notes to the list
#             if retval and notes.strip():
#                 items_with_notes.append({"item_index": i, "notes": notes})

#     # Return the list of dictionaries or an empty list if no notes were found
#     return items_with_notes

# # Execute the function and print the result
# result = find_items_with_notes_at_play_position()
# print(result)