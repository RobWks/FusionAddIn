import adsk.core
import adsk.fusion
import adsk.cam
import math

# Import the entire apper package
import apper

# Alternatively you can import a specific function or class
from apper import AppObjects


# Class for a Fusion 360 Command
# Place your program logic here
# Delete the line that says "pass" for any method you want to use
class Polyline(apper.Fusion360CommandBase):
 
    # Run whenever a user makes any change to a value or selection in the addin UI
    # Commands in here will be run through the Fusion processor and changes will be reflected in  Fusion graphics area
    def on_preview(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        # Get the values from the user input
        the_value = input_values['offset_input_id']
        #the_boolean = input_values['bool_input_id']
        #the_string = input_values['string_input_id']
        all_selections = input_values['selection_input_id']
        #the_drop_down = input_values['drop_down_input_id']
        
        # Selections are returned as a list so lets get the first one and its name
        for the_first_selection in all_selections:
            #the_first_selection = all_selections[0]
            sketch_select = the_first_selection.parentSketch
            the_selection_type = the_first_selection.objectType
            
            curve_path = sketch_select.findConnectedCurves(the_first_selection)
            #curve_path_twin = sketch_select.copy(curve_path)
            """
            if len(curve_path) > 1:
                for line1,line2 in zip(curve_path[:-1],curve_path[1:]):
                    sketch_select.sketchCurves.sketchArcs.addFillet(line1, line1.endSketchPoint.geometry, line2, line2.startSketchPoint.geometry, 0.01)
            """

            app = adsk.core.Application.get()
            product = app.activeProduct
            design = adsk.fusion.Design.cast(product)    

            # define root component
            rootComp = design.rootComponent
            sketches = rootComp.sketches

            # Get construction planes
            planes = rootComp.constructionPlanes
            
            # Create construction plane input
            planeInput = planes.createInput()

            # Create startPoint Plane
            distance = adsk.core.ValueInput.createByReal(0.0)
            planeInput.setByDistanceOnPath(curve_path.item(0), distance)
            planes.add(planeInput)

            # Create endPoint Plane
            distance = adsk.core.ValueInput.createByReal(1.0)
            planeInput.setByDistanceOnPath(curve_path.item(curve_path.count-1), distance)
            planes.add(planeInput)
            
            # Create sketches
            sketch_startPoint = sketches.add(planes.item(planes.count-2))
            sketch_endPoint = sketches.add(planes.item(planes.count-1))

            # Create sketch circle to each
            centerPoint = adsk.core.Point3D.create(0, 0, 0)
            sketch_startPoint.sketchCurves.sketchCircles.addByCenterRadius(centerPoint, the_value/2) 
            sketch_endPoint.sketchCurves.sketchCircles.addByCenterRadius(centerPoint, the_value/2)  
            
            # Start by creating the sweep feature
            # Get the profile defined by the circle
            prof = sketch_startPoint.profiles.item(0)
            path = rootComp.features.createPath(curve_path.item(0))
            
            # Create a sweep input
            sweeps = rootComp.features.sweepFeatures
            sweepInput = sweeps.createInput(prof, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

            # Create the sweep.
            sweep = sweeps.add(sweepInput)
            
            if not curve_path.item(0) == curve_path.item(curve_path.count-1):
                # Create new half circle profiles
                axisLine_startPoint = sketch_startPoint.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(-3, 0, 0), adsk.core.Point3D.create(3, 0, 0))
                prof_startPoint = sketch_startPoint.profiles.item(0)
                
                axisLine_endPoint = sketch_endPoint.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(-3, 0, 0), adsk.core.Point3D.create(3, 0, 0))
                prof_endPoint = sketch_endPoint.profiles.item(0)
                
                revolves = rootComp.features.revolveFeatures
                revInput_startPoint = revolves.createInput(prof_startPoint, axisLine_startPoint, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                revInput_endPoint = revolves.createInput(prof_endPoint, axisLine_endPoint, adsk.fusion.FeatureOperations.JoinFeatureOperation)

                # Define that the extent is an angle of 2*pi to get a sphere
                angle = adsk.core.ValueInput.createByReal(2*math.pi)
                revInput_startPoint.setAngleExtent(False, angle)
                revInput_endPoint.setAngleExtent(False, angle)

                # Create the extrusion.
                ext1 = revolves.add(revInput_startPoint)
                ext2 = revolves.add(revInput_endPoint)

                # Delete Axis line 
                axisLine_startPoint.deleteMe()
                axisLine_endPoint.deleteMe()

            sketch_select.isVisible=True

    # Run after the command is finished.
    # Can be used to launch another command automatically or do other clean up.
    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, reason, input_values):
        pass

    # Run when any input is changed.
    # Can be used to check a value and then update the add-in UI accordingly
    def on_input_changed(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, changed_input, input_values):
        pass
        """
        # Selections are returned as a list so lets get the first one
        all_selections = input_values.get('selection_input_id', None)

        if all_selections is not None:
            the_first_selection = all_selections[0]

            # Update the text of the string value input to show the type of object selected
            text_box_input = inputs.itemById('text_box_input_id')
            text_box_input.text = the_first_selection.objectType
        """

    # Run when the user presses OK
    # This is typically where your main program logic would go
    def on_execute(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        # Get the values from the user input
        the_value = input_values['offset_input_id']
        #the_boolean = input_values['bool_input_id']
        #the_string = input_values['string_input_id']
        all_selections = input_values['selection_input_id']
        #the_drop_down = input_values['drop_down_input_id']
        
        # Selections are returned as a list so lets get the first one and its name
        for the_first_selection in all_selections:
            #the_first_selection = all_selections[0]
            sketch_select = the_first_selection.parentSketch
            the_selection_type = the_first_selection.objectType
            
            curve_path = sketch_select.findConnectedCurves(the_first_selection)
  
            if len(curve_path) > 1:
                for line1,line2 in zip(curve_path[:-1],curve_path[1:]):
                    sketch_select.sketchCurves.sketchArcs.addFillet(line1, line1.endSketchPoint.geometry, line2, line2.startSketchPoint.geometry, 0.01)

            app = adsk.core.Application.get()
            product = app.activeProduct
            design = adsk.fusion.Design.cast(product)    

            # define root component
            rootComp = design.rootComponent
            sketches = rootComp.sketches

            # Get construction planes
            planes = rootComp.constructionPlanes
            
            # Create construction plane input
            planeInput = planes.createInput()

            # Create startPoint Plane
            distance = adsk.core.ValueInput.createByReal(0.0)
            planeInput.setByDistanceOnPath(curve_path.item(0), distance)
            planes.add(planeInput)

            # Create endPoint Plane
            distance = adsk.core.ValueInput.createByReal(1.0)
            planeInput.setByDistanceOnPath(curve_path.item(curve_path.count-1), distance)
            planes.add(planeInput)
            
            # Create sketches
            sketch_startPoint = sketches.add(planes.item(planes.count-2))
            sketch_endPoint = sketches.add(planes.item(planes.count-1))

            # Create sketch circle to each
            centerPoint = adsk.core.Point3D.create(0, 0, 0)
            sketch_startPoint.sketchCurves.sketchCircles.addByCenterRadius(centerPoint, the_value/2) 
            sketch_endPoint.sketchCurves.sketchCircles.addByCenterRadius(centerPoint, the_value/2)  
            
            # Start by creating the sweep feature
            # Get the profile defined by the circle
            prof = sketch_startPoint.profiles.item(0)
            path = rootComp.features.createPath(curve_path.item(0))
            
            # Create a sweep input
            sweeps = rootComp.features.sweepFeatures
            sweepInput = sweeps.createInput(prof, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

            # Create the sweep.
            sweep = sweeps.add(sweepInput)
            
            if not curve_path.item(0) == curve_path.item(curve_path.count-1):
                # Create new half circle profiles
                axisLine_startPoint = sketch_startPoint.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(-3, 0, 0), adsk.core.Point3D.create(3, 0, 0))
                prof_startPoint = sketch_startPoint.profiles.item(0)
                
                axisLine_endPoint = sketch_endPoint.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(-3, 0, 0), adsk.core.Point3D.create(3, 0, 0))
                prof_endPoint = sketch_endPoint.profiles.item(0)
                
                revolves = rootComp.features.revolveFeatures
                revInput_startPoint = revolves.createInput(prof_startPoint, axisLine_startPoint, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                revInput_endPoint = revolves.createInput(prof_endPoint, axisLine_endPoint, adsk.fusion.FeatureOperations.JoinFeatureOperation)

                # Define that the extent is an angle of 2*pi to get a sphere
                angle = adsk.core.ValueInput.createByReal(2*math.pi)
                revInput_startPoint.setAngleExtent(False, angle)
                revInput_endPoint.setAngleExtent(False, angle)

                # Create the extrusion.
                ext1 = revolves.add(revInput_startPoint)
                ext2 = revolves.add(revInput_endPoint)

                # Delete Axis line 
                axisLine_startPoint.deleteMe()
                axisLine_endPoint.deleteMe()

            sketch_select.isVisible=True
        
        """
        # Get a reference to all relevant application objects in a dictionary
        ao = AppObjects()

        converted_value = ao.units_manager.formatInternalValue(the_value, 'in', True)

        ao.ui.messageBox('The value, in internal units, you entered was:  {} \n'.format(planes.count) +
                         'The value, in inches, you entered was:  {} \n'.format(the_selection_type)
                         #'The boolean value checked was:  {} \n'.format(the_boolean) +
                         #'The string you typed was:  {} \n'.format(the_string) +
                         #'The type of the first object you selected is:  {} \n'.format(bb) +
                         #'The drop down item you selected is:  {}'.format(the_drop_down)
                         )
        """

    # Run when the user selects your command icon from the Fusion 360 UI
    # Typically used to create and display a command dialog box
    # The following is a basic sample of a dialog UI

    def on_create(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):

        ao = AppObjects()

        # Create a default value using a string
        default_value = adsk.core.ValueInput.createByString('2 mm')

        # Get teh user's current units
        default_units = ao.units_manager.defaultLengthUnits

        # Create a value input.  This will respect units and user defined equation input.
        inputs.addValueInput('offset_input_id', '*Sample* Value Input', default_units, default_value)

        # Other Input types
        #inputs.addBoolValueInput('bool_input_id', '*Sample* Check Box', True)
        #inputs.addStringValueInput('string_input_id', '*Sample* String Value', 'Some Default Value')
        selectionCommandInput = inputs.addSelectionInput('selection_input_id', 'Area', 'Select Area')
        selectionCommandInput.setSelectionLimits(0, 0)

        # Read Only Text Box
        #inputs.addTextBoxCommandInput('text_box_input_id', 'Selection Type: ', 'Nothing Selected', 1, True)

        # Create a Drop Down
        #drop_down_input = inputs.addDropDownCommandInput('drop_down_input_id', '*Sample* Drop Down',
        #                                                 adsk.core.DropDownStyles.TextListDropDownStyle)
        #drop_down_items = drop_down_input.listItems
        #drop_down_items.add('List_Item_1', True, '')
        #drop_down_items.add('List_Item_2', False, '')

