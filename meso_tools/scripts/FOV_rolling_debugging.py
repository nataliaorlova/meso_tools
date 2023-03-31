from meso_tools import read_scanimage_metadata, read_scanimage_stack_metadata, read_plane_in_stack

stack_path = r"E:\FOV_rolling_debug_March2023\cortical_stack_100planes_100loops.tif"
meta = read_scanimage_metadata(stack_path)
stack_meta = read_scanimage_stack_metadata(meta)
repeats = stack_meta['num_volumes']
slices = stack_meta['num_slices']

for plane in range(slices):
    plane, repeats = read_plane_in_stack(stack_path, plane, slices)