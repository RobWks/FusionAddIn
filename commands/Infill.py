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
class Infill(apper.Fusion360CommandBase):
    def linspace(self,start, stop, n):
        if n == 1:
            yield stop
            return
        h = (stop - start) / (n - 1)
        for i in range(n):
            yield start + h * i    

    def getPointInClosedCurves(self,skCurves):
        # Function that's used to get the value to sort with.
        def getKey(item):
            return item[1]

                    
        # Calculate the intersection between two line segments.  This is based on the JS
        # sample in the second answer at:
        # http://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect
        def getLineIntersection(p0_x, p0_y, p1_x, p1_y, p2_x, p2_y, p3_x, p3_y):
            s1_x = p1_x - p0_x
            s1_y = p1_y - p0_y
            s2_x = p3_x - p2_x
            s2_y = p3_y - p2_y

            s = (-s1_y * (p0_x - p2_x) + s1_x * (p0_y - p2_y)) / (-s2_x * s1_y + s1_x * s2_y)
            t = ( s2_x * (p0_y - p2_y) - s2_y * (p0_x - p2_x)) / (-s2_x * s1_y + s1_x * s2_y)

            if (s >= 0 and s <= 1 and t >= 0 and t <= 1):
                # Collision detected
                i_x = p0_x + (t * s1_x)
                i_y = p0_y + (t * s1_y)
                return (i_x, i_y)

            return False  # No collision
        
        try:
            # Build up list of connected points.
            curve = adsk.fusion.SketchCurve.cast(None)
            pointSets = []
            boundBox = None
            for curve in skCurves:
                if not boundBox:
                    boundBox = curve.boundingBox
                else:
                    boundBox.combine(curve.boundingBox)            
                    
                if isinstance(curve, adsk.fusion.SketchLine):
                    skLine = adsk.fusion.SketchLine.cast(curve)
                    pointSets.append((skLine.startSketchPoint.geometry, skLine.endSketchPoint.geometry))
                else:
                    curveEval = adsk.core.CurveEvaluator3D.cast(curve.geometry.evaluator)
                    (retVal, startParam, endParam) = curveEval.getParameterExtents()
                    
                    (retVal, strokePoints) = curveEval.getStrokes(startParam, endParam, 0.1)
                    pointSets.append(strokePoints)
                
            # Create two points that define a line that crosses the entire range.  They're moved
            # to be outside the bounding box so there's not problem with coincident points.
            lineVec = boundBox.minPoint.vectorTo(boundBox.maxPoint)
            lineVec.normalize()
            maxPoint = boundBox.maxPoint.copy()
            maxPoint.translateBy(lineVec)
            lineVec.scaleBy(-1)
            minPoint = boundBox.minPoint.copy()
            minPoint.translateBy(lineVec)
        
            # Iterate through all of the lines and get the intersection between the lines
            # and the long crossing line.
            intPointList = []
            for pointSet in pointSets:
                pnt1 = None
                pnt2 = None
                for point in pointSet:
                    if not pnt2:
                        pnt2 = point
                    else:
                        pnt1 = pnt2
                        pnt2 = point
        
                        intCoords = getLineIntersection(minPoint.x, minPoint.y, maxPoint.x, maxPoint.y, pnt1.x, pnt1.y, pnt2.x, pnt2.y)
                        if intCoords:
                            intPoint = adsk.core.Point3D.create(intCoords[0], intCoords[1], 0)
                            intPointList.append((intPoint, intPoint.distanceTo(minPoint)))
            
            # Make sure at last two intersection points were found.
            if len(intPointList) >= 2:
                # Sort the points by the distance from the min point.
                sortedPoints = sorted(intPointList, key=getKey) 
            
                # Get the first two points and compute a mid point.  That's a point in the area.                
                pnt1 = sortedPoints[0]
                pnt2 = sortedPoints[1]
                midPoint = adsk.core.Point3D.create((pnt1[0].x + pnt2[0].x)/2, (pnt1[0].y + pnt2[0].y)/2, 0)
                return midPoint
            else:
                return False
        except:
            ui = adsk.core.Application.get().userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))  

    # Run whenever a user makes any change to a value or selection in the addin UI
    # Commands in here will be run through the Fusion processor and changes will be reflected in  Fusion graphics area
    def on_preview(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):

        # Get the values from the user input
        the_value = input_values['infill_spacing_input_id']
        the_angle = input_values['infill_angle_input_id']
        #the_boolean = input_values['bool_input_id']
        #the_string = input_values['string_input_id']
        all_selections = input_values['area_selection_input_id']
        the_drop_down = input_values['start_loc_input_id']
        perimeter_layers = input_values['perimeter_input_id']
        
        # Selections are returned as a list so lets get the first one and its name
        the_first_selection = all_selections[0]

        sketch_select = the_first_selection.parentSketch
        profile_curves_sketch = adsk.core.ObjectCollection.create()
        stripe_curves = adsk.core.ObjectCollection.create()
        outside_curves = adsk.core.ObjectCollection.create()
        inside_curves = adsk.core.ObjectCollection.create()
        intersect_test = adsk.core.ObjectCollection.create() 
        all_intersect_points = adsk.core.ObjectCollection.create() 

        # Offset profiles
        loops = the_first_selection.profileLoops  
        maxP = the_first_selection.boundingBox.maxPoint
        minP = the_first_selection.boundingBox.minPoint
                  
        for loop in loops:
            if loop.isOuter:
                for curve in loop.profileCurves:
                    outside_curves.add(curve.sketchEntity)
            else:
                for curve in loop.profileCurves:
                    inside_curves.add(curve.sketchEntity)
                    bb = curve.boundingBox.maxPoint
      
        pnt = self.getPointInClosedCurves(outside_curves)
        
        for perimeter_layer in range(perimeter_layers+1):
            infill_perimeter = sketch_select.offset(outside_curves, pnt, the_value*(perimeter_layer)+the_value/2).item(0)
        
        # Find mid point of first selection
        bbox_max_point = infill_perimeter.boundingBox.maxPoint
        bbox_min_point = infill_perimeter.boundingBox.minPoint
        bbox_max = bbox_max_point.asArray()
        bbox_min = bbox_min_point.asArray()
        mid_point = [(bbox_max[0]+bbox_min[0])/2,(bbox_max[1]+bbox_min[1])/2,bbox_max[2]]
        bbox_mid_point = adsk.core.Point3D.create(*mid_point)

        # Calculate transformation matrix for given angle
        normal = sketch_select.xDirection.crossProduct(sketch_select.yDirection)
        normal.transformBy(sketch_select.transform)
        mat = adsk.core.Matrix3D.create()
        mat.setToRotation(the_angle, normal, bbox_mid_point)

        # Rotate selection
        profile_curves_sketch.add(infill_perimeter)
        sketch_select.move(profile_curves_sketch,mat)

        # Find bounding box for rotated version
        bbox_max_point = profile_curves_sketch.item(0).boundingBox.maxPoint.copy()
        bbox_min_point = profile_curves_sketch.item(0).boundingBox.minPoint.copy()
        bbox_max = list(bbox_max_point.asArray())
        bbox_min = list(bbox_min_point.asArray())
        bbox_max[1] += 0.1*math.copysign(1,bbox_max[1])*bbox_max[1]
        bbox_min[1] -= 0.1*math.copysign(1,bbox_min[1])*bbox_min[1]

        # Rotate back the selection
        mat.setToRotation(-the_angle, normal, bbox_mid_point)
        sketch_select.move(profile_curves_sketch,mat)

        # DEBUGGING
        #bbox_max_point.transformBy(mat)
        #bbox_min_point.transformBy(mat)
        #sketch_select.sketchPoints.add(bbox_min_point)
        #sketch_select.sketchPoints.add(bbox_max_point)
        
        spacing = math.ceil((bbox_max[0]-bbox_min[0])/the_value)
        adjusted_spacing = (bbox_max[0]-bbox_min[0])/spacing
        ao = AppObjects()
        converted_value = ao.units_manager.formatInternalValue(adjusted_spacing, 'mm', False)
        text_box_input = inputs.itemById('text_box_input_id')
        text_box_input.text = "{:.3f} mm".format(float(converted_value))
        generator = list(self.linspace(bbox_min[0]-the_value/2,bbox_max[0]+the_value/2,spacing+1))

        for i,infill_line in enumerate(generator[1:-1]):
            point1 = adsk.core.Point3D.create(infill_line,bbox_min[1],bbox_min[2])
            point2 = adsk.core.Point3D.create(infill_line,bbox_max[1],bbox_max[2])
            point1.transformBy(mat)
            point2.transformBy(mat)
            stripe = sketch_select.sketchCurves.sketchLines.addByTwoPoints(point1, point2)

            intersect_test.add(stripe)
            (returnValue, intersectingCurves, intersectionPoints) = infill_perimeter.intersections(intersect_test)

            p1 = intersectionPoints.item(0).asArray()
            p2 = intersectionPoints.item(1).asArray()
            
            if the_drop_down == 'Top Left' or (the_drop_down == 'Top Right' and not (spacing+1)%2) or (the_drop_down == 'Bottom Right' and (spacing+1)%2):
                i+=1

            if (not i%2 and p1[1] < p2[1]) or (i%2 and p1[1] > p2[1]):
                all_intersect_points.add(intersectionPoints.item(0))
                all_intersect_points.add(intersectionPoints.item(1))
            else:
                all_intersect_points.add(intersectionPoints.item(1))
                all_intersect_points.add(intersectionPoints.item(0))

            intersect_test.clear()
            stripe.deleteMe()

        new_line = sketch_select.sketchCurves.sketchLines.addByTwoPoints(all_intersect_points.item(0), all_intersect_points.item(1))
        for point in all_intersect_points[2:]:
            new_line = sketch_select.sketchCurves.sketchLines.addByTwoPoints(new_line.endSketchPoint, point)

        infill_perimeter.deleteMe()
        for loop in the_first_selection.profileLoops:
            for curve in loop.profileCurves:
                curve.sketchEntity.deleteMe()

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
        the_value = input_values['infill_spacing_input_id']
        the_angle = input_values['infill_angle_input_id']
        #the_boolean = input_values['bool_input_id']
        #the_string = input_values['string_input_id']
        all_selections = input_values['area_selection_input_id']
        the_drop_down = input_values['start_loc_input_id']
        perimeter_layers = input_values['perimeter_input_id']
        
        # Selections are returned as a list so lets get the first one and its name
        the_first_selection = all_selections[0]

        sketch_select = the_first_selection.parentSketch
        profile_curves_sketch = adsk.core.ObjectCollection.create()
        stripe_curves = adsk.core.ObjectCollection.create()
        outside_curves = adsk.core.ObjectCollection.create()
        inside_curves = adsk.core.ObjectCollection.create()
        intersect_test = adsk.core.ObjectCollection.create() 
        all_intersect_points = adsk.core.ObjectCollection.create() 

        # Offset profiles
        loops = the_first_selection.profileLoops  
        maxP = the_first_selection.boundingBox.maxPoint
        minP = the_first_selection.boundingBox.minPoint
                  
        for loop in loops:
            if loop.isOuter:
                for curve in loop.profileCurves:
                    outside_curves.add(curve.sketchEntity)
            else:
                for curve in loop.profileCurves:
                    inside_curves.add(curve.sketchEntity)
                    bb = curve.boundingBox.maxPoint
      
        pnt = self.getPointInClosedCurves(outside_curves)
        
        for perimeter_layer in range(perimeter_layers+1):
            infill_perimeter = sketch_select.offset(outside_curves, pnt, the_value*(perimeter_layer)+the_value/2).item(0)
        
        # Find mid point of first selection
        bbox_max_point = infill_perimeter.boundingBox.maxPoint
        bbox_min_point = infill_perimeter.boundingBox.minPoint
        bbox_max = bbox_max_point.asArray()
        bbox_min = bbox_min_point.asArray()
        mid_point = [(bbox_max[0]+bbox_min[0])/2,(bbox_max[1]+bbox_min[1])/2,bbox_max[2]]
        bbox_mid_point = adsk.core.Point3D.create(*mid_point)

        # Calculate transformation matrix for given angle
        normal = sketch_select.xDirection.crossProduct(sketch_select.yDirection)
        normal.transformBy(sketch_select.transform)
        mat = adsk.core.Matrix3D.create()
        mat.setToRotation(the_angle, normal, bbox_mid_point)

        # Rotate selection
        profile_curves_sketch.add(infill_perimeter)
        sketch_select.move(profile_curves_sketch,mat)

        # Find bounding box for rotated version
        bbox_max_point = profile_curves_sketch.item(0).boundingBox.maxPoint.copy()
        bbox_min_point = profile_curves_sketch.item(0).boundingBox.minPoint.copy()
        bbox_max = list(bbox_max_point.asArray())
        bbox_min = list(bbox_min_point.asArray())
        bbox_max[1] += 0.1*math.copysign(1,bbox_max[1])*bbox_max[1]
        bbox_min[1] -= 0.1*math.copysign(1,bbox_min[1])*bbox_min[1]

        # Rotate back the selection
        mat.setToRotation(-the_angle, normal, bbox_mid_point)
        sketch_select.move(profile_curves_sketch,mat)

        # DEBUGGING
        #bbox_max_point.transformBy(mat)
        #bbox_min_point.transformBy(mat)
        #sketch_select.sketchPoints.add(bbox_min_point)
        #sketch_select.sketchPoints.add(bbox_max_point)
        
        spacing = math.ceil((bbox_max[0]-bbox_min[0])/the_value)
        adjusted_spacing = (bbox_max[0]-bbox_min[0])/spacing
        ao = AppObjects()
        converted_value = ao.units_manager.formatInternalValue(adjusted_spacing, 'mm', False)
        text_box_input = inputs.itemById('text_box_input_id')
        text_box_input.text = "{:.3f} mm".format(float(converted_value))
        generator = list(self.linspace(bbox_min[0]-the_value/2,bbox_max[0]+the_value/2,spacing+1))

        for i,infill_line in enumerate(generator[1:-1]):
            point1 = adsk.core.Point3D.create(infill_line,bbox_min[1],bbox_min[2])
            point2 = adsk.core.Point3D.create(infill_line,bbox_max[1],bbox_max[2])
            point1.transformBy(mat)
            point2.transformBy(mat)
            stripe = sketch_select.sketchCurves.sketchLines.addByTwoPoints(point1, point2)

            intersect_test.add(stripe)
            (returnValue, intersectingCurves, intersectionPoints) = infill_perimeter.intersections(intersect_test)

            p1 = intersectionPoints.item(0).asArray()
            p2 = intersectionPoints.item(1).asArray()
            
            if the_drop_down == 'Top Left' or (the_drop_down == 'Top Right' and not (spacing+1)%2) or (the_drop_down == 'Bottom Right' and (spacing+1)%2):
                i+=1

            if (not i%2 and p1[1] < p2[1]) or (i%2 and p1[1] > p2[1]):
                all_intersect_points.add(intersectionPoints.item(0))
                all_intersect_points.add(intersectionPoints.item(1))
            else:
                all_intersect_points.add(intersectionPoints.item(1))
                all_intersect_points.add(intersectionPoints.item(0))

            intersect_test.clear()
            stripe.deleteMe()

        new_line = sketch_select.sketchCurves.sketchLines.addByTwoPoints(all_intersect_points.item(0), all_intersect_points.item(1))
        for point in all_intersect_points[2:]:
            new_line = sketch_select.sketchCurves.sketchLines.addByTwoPoints(new_line.endSketchPoint, point)

        infill_perimeter.deleteMe()
        for loop in the_first_selection.profileLoops:
            for curve in loop.profileCurves:
                curve.sketchEntity.deleteMe()
        """
        ao = AppObjects()

        converted_value = ao.units_manager.formatInternalValue(the_value, 'in', True)

        ao.ui.messageBox('The value, in internal units, you entered was:  {} \n'.format(bbox_max_point.asArray()) +
                         #'The value, in inches, you entered was:  {} \n'.format(converted_value) +
                         #'The boolean value checked was:  {} \n'.format(the_boolean) +
                         #'The string you typed was:  {} \n'.format(the_string) +
                         #'The type of the first object you selected is:  {} \n'.format(the_value) +
                         'The drop down item you selected is:  {}'.format(the_drop_down)
                         )
        """

    # Run when the user selects your command icon from the Fusion 360 UI
    # Typically used to create and display a command dialog box
    # The following is a basic sample of a dialog UI

    def on_create(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):

        ao = AppObjects()

        # Create a default value using a string
        default_value = adsk.core.ValueInput.createByString('2 mm')
        default_angle_value = adsk.core.ValueInput.createByString('0 deg')
        # Get the user's current units
        default_units = ao.units_manager.defaultLengthUnits

        # Other Input types
        #inputs.addBoolValueInput('bool_input_id', '*Sample* Check Box', True)
        #inputs.addStringValueInput('string_input_id', '*Sample* String Value', 'Some Default Value')
        inputs.addSelectionInput('area_selection_input_id', 'Area', 'Select Area')

        # Create a value input.  This will respect units and user defined equation input.
        inputs.addValueInput('infill_spacing_input_id', 'Infill Spacing', default_units, default_value)
        inputs.addValueInput('infill_angle_input_id', 'Infill Angle', 'deg', default_angle_value)

        # Read Only Text Box
        inputs.addTextBoxCommandInput('text_box_input_id', 'Actual Spacing ', '', 1, True)

        # Create a Drop Down
        drop_down_input = inputs.addDropDownCommandInput('start_loc_input_id', 'Start Location',
                                                         adsk.core.DropDownStyles.TextListDropDownStyle)
        drop_down_items = drop_down_input.listItems
        drop_down_items.add('Bottom Left', True, '')
        drop_down_items.add('Top Left', False, '')
        drop_down_items.add('Top Right', False, '')
        drop_down_items.add('Bottom Right', False, '')

        # Add int spinner
        spinner_input = inputs.addIntegerSpinnerCommandInput('perimeter_input_id', 'Perimeter Count', 0, 10, 1, 0)