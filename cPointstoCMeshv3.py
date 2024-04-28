import csv
import salome
import GEOM
import SMESH
import math
import SALOMEDS
salome.salome_init_without_session()
from salome.geom import geomBuilder
from salome.smesh import smeshBuilder
from salome.shaper import model
gg = salome.ImportComponentGUI("GEOM")
geom_builder = geomBuilder.New()
smesh_builder = smeshBuilder.New()

# from salomeToOpenFOAM import exportToFoam
import salomeToOpenFOAM


###
### SALOME SHAPER - AIRFOIL CREATION
###
def salome_stuff(xC, yC, zC, outdir):
    model.begin()
    partSet = model.moduleDocument()
    Part_1 = model.addPart(partSet)
    Part_1_doc = Part_1.document()
    Sketch_1 = model.addSketch(Part_1_doc, model.defaultPlane("XOY"))

    SketchBSpline_1_poles = [(float(xC[0]),float(yC[0])),
                            (float(xC[1]),float(yC[1])),
                            (float(xC[2]),float(yC[2])),
                            (float(xC[3]),float(yC[3])),
                            (float(xC[4]),float(yC[4])),
                            (float(xC[5]),float(yC[5]))
                            ]
    SketchBSpline_2_poles = [(float(xC[6]),float(yC[6])),
                            (float(xC[7]),float(yC[7])),
                            (float(xC[8]),float(yC[8])),
                            (float(xC[9]),float(yC[9])),
                            (float(xC[10]),float(yC[10])),
                            (float(xC[11]),float(yC[11]))
                            ]
    SketchBSpline_3_poles = [(float(xC[12]),float(yC[12])),
                            (float(xC[13]),float(yC[13])),
                            (float(xC[14]),float(yC[14])),
                            (float(xC[15]),float(yC[15])),
                            (float(xC[16]),float(yC[16])),
                            (float(xC[17]),float(yC[17]))
                            ]
    SketchBSpline_1 = Sketch_1.addSpline(degree =5, poles = SketchBSpline_1_poles, periodic = False)
    [SketchPoint_1, SketchPoint_2, SketchPoint_3, SketchPoint_4, SketchPoint_5, SketchPoint_6] = SketchBSpline_1.controlPoles(auxiliary = [0, 1, 2, 3, 4, 5])
    [SketchLine_1, SketchLine_2, SketchLine_3, SketchLine_4, SketchLine_5] = SketchBSpline_1.controlPolygon(auxiliary = [0, 1, 2, 3, 4])

    SketchBSpline_2 = Sketch_1.addSpline(degree =5, poles = SketchBSpline_2_poles, periodic = False)
    [SketchPoint_7, SketchPoint_8, SketchPoint_9, SketchPoint_10, SketchPoint_11, SketchPoint_12] = SketchBSpline_1.controlPoles(auxiliary = [0, 1, 2, 3, 4, 5])
    [SketchLine_7, SketchLine_8, SketchLine_9, SketchLine_10, SketchLine_11] = SketchBSpline_1.controlPolygon(auxiliary = [0, 1, 2, 3, 4])

    SketchBSpline_3 = Sketch_1.addSpline(degree =5, poles = SketchBSpline_3_poles, periodic = False)
    [SketchPoint_13, SketchPoint_14, SketchPoint_15, SketchPoint_16, SketchPoint_17, SketchPoint_18] = SketchBSpline_1.controlPoles(auxiliary = [0, 1, 2, 3, 4, 5])
    [SketchLine_13, SketchLine_14, SketchLine_15, SketchLine_16, SketchLine_17] = SketchBSpline_1.controlPolygon(auxiliary = [0, 1, 2, 3, 4])

    #exports airfoil
    buffer = model.exportToXAOMem(Part_1_doc, model.selection("COMPOUND", "Sketch_1"),"","airfoil")
    model.do()
    model.end()

    ###
    ### SALOME GEOM - CREATE GROUPS FOR MESH
    ###
    geompy = geomBuilder.New()

    O = geompy.MakeVertex(0, 0, 0)
    OX = geompy.MakeVectorDXDYDZ(1, 0, 0)
    OY = geompy.MakeVectorDXDYDZ(0, 1, 0)
    OZ = geompy.MakeVectorDXDYDZ(0, 0, 1)

    #imports airfoil geo from shaper
    (imported, airfoil, [], [], []) = geompy.ImportXAOMem(buffer)
    #geomObj_23 = geompy.MakeTranslation(airfoil, 0, 0, -0.5)

    #Make boundary region
    Disk_1 = geompy.MakeDiskR(10, 1)
    Face_1 = geompy.MakeFaceHW(10, 20, 1)
    Translation_1 = geompy.MakeTranslation(Face_1, 5, 0, 0)
    Fuse_1 = geompy.MakeFuseList([Disk_1, Translation_1], True, True)
    Translation_2 = geompy.MakeTranslation(Fuse_1, 1, 0, 0)
    Disk_2 = geompy.MakeDiskR(20, 3)
    Disk_3 = geompy.MakeDiskR(20, 2)
    Translation_3 = geompy.MakeTranslation(Disk_3, 1, 0, 0)
    Partition_1 = geompy.MakePartition([Translation_2], [airfoil, Disk_2, Translation_3], [], [], geompy.ShapeType["SHELL"], 0, [], 0)
    SuppressFaces_1 = geompy.SuppressFaces(Partition_1, [29, 32])

    #Create groups for meshing
    FarField = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["EDGE"])
    geompy.UnionIDs(FarField, [33, 31, 18, 16, 28, 13])
    Airfoil = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["EDGE"])
    geompy.UnionIDs(Airfoil, [7, 9, 25, 23])
    Left = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["EDGE"])
    geompy.UnionIDs(Left, [11])
    Right = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["EDGE"])
    geompy.UnionIDs(Right, [20])
    Top = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["EDGE"])
    geompy.UnionIDs(Top, [4])
    Bottom = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["EDGE"])
    geompy.UnionIDs(Bottom, [26])
    [FarField, Airfoil, Left, Right, Top, Bottom] = geompy.GetExistingSubObjects(SuppressFaces_1, False)
    geomObj_24 = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["FACE"])
    geompy.UnionIDs(geomObj_24, [14, 29])
    TopLeft = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["FACE"])
    geompy.UnionIDs(TopLeft, [2])
    BottomLeft = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["FACE"])
    geompy.UnionIDs(BottomLeft, [21])
    geomObj_25 = geompy.GetSubShape(SuppressFaces_1, [26])
    geomObj_26 = geompy.GetSubShape(SuppressFaces_1, [33])
    geomObj_27 = geompy.GetSubShape(SuppressFaces_1, [31])
    geomObj_28 = geompy.GetSubShape(SuppressFaces_1, [18])
    geomObj_29 = geompy.GetSubShape(SuppressFaces_1, [16])
    geomObj_30 = geompy.GetSubShape(SuppressFaces_1, [28])
    geomObj_31 = geompy.GetSubShape(SuppressFaces_1, [13])
    TopRight = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["FACE"])
    geompy.UnionIDs(TopRight, [14])
    BottomRight = geompy.CreateGroup(SuppressFaces_1, geompy.ShapeType["FACE"])
    geompy.UnionIDs(BottomRight, [29])
    [FarField, Airfoil, Left, Right, Top, Bottom, geomObj_24, TopLeft, BottomLeft, geomObj_25, geomObj_26, geomObj_27, geomObj_28, geomObj_29, geomObj_30, geomObj_31, TopRight, BottomRight] = geompy.GetExistingSubObjects(SuppressFaces_1, False)

    geompy.addToStudy( O, 'O' )
    geompy.addToStudy( OX, 'OX' )
    geompy.addToStudy( OY, 'OY' )
    geompy.addToStudy( OZ, 'OZ' )
    geompy.addToStudy( airfoil, 'airfoil' )
    geompy.addToStudy( Disk_1, 'Disk_1' )
    geompy.addToStudy( Face_1, 'Face_1' )
    geompy.addToStudy( Translation_1, 'Translation_1' )
    geompy.addToStudy( Fuse_1, 'Fuse_1' )
    geompy.addToStudy( Translation_2, 'Translation_2' )
    geompy.addToStudy( Disk_2, 'Disk_2' )
    geompy.addToStudy( Disk_3, 'Disk_3' )
    geompy.addToStudy( Translation_3, 'Translation_3' )
    geompy.addToStudy( Partition_1, 'Partition_1' )
    geompy.addToStudy( SuppressFaces_1, 'SuppressFaces_1' )
    geompy.addToStudyInFather( SuppressFaces_1, FarField, 'FarField' )
    geompy.addToStudyInFather( SuppressFaces_1, Airfoil, 'Airfoil' )
    geompy.addToStudyInFather( SuppressFaces_1, Left, 'Left' )
    geompy.addToStudyInFather( SuppressFaces_1, Right, 'Right' )
    geompy.addToStudyInFather( SuppressFaces_1, Top, 'Top' )
    geompy.addToStudyInFather( SuppressFaces_1, Bottom, 'Bottom' )
    geompy.addToStudyInFather( SuppressFaces_1, TopLeft, 'TopLeft' )
    geompy.addToStudyInFather( SuppressFaces_1, BottomLeft, 'BottomLeft' )
    geompy.addToStudyInFather( SuppressFaces_1, TopRight, 'TopRight' )
    geompy.addToStudyInFather( SuppressFaces_1, BottomRight, 'BottomRight' )


    ###
    ### SALOME MESH - CREATE MESH
    ###
    smesh = smeshBuilder.New()
    #smesh.SetEnablePublish( False ) # Set to False to avoid publish in study if not needed or in some particular situations:
                                    # multiples meshes built in parallel, complex and numerous mesh edition (performance)

    Mesh_1 = smesh.Mesh(SuppressFaces_1,'Mesh_1')
    Regular_1D = Mesh_1.Segment()
    Mesh = Regular_1D.LocalLength(0.1,None,1e-07)
    Quadrangle_2D = Mesh_1.Quadrangle(algo=smeshBuilder.QUADRANGLE)
    FarField_1 = Mesh_1.GroupOnGeom(FarField,'FarField',SMESH.EDGE)
    Airfoil_1 = Mesh_1.GroupOnGeom(Airfoil,'Airfoil',SMESH.EDGE)
    Left_1 = Mesh_1.GroupOnGeom(Left,'Left',SMESH.EDGE)
    Right_1 = Mesh_1.GroupOnGeom(Right,'Right',SMESH.EDGE)
    Top_1 = Mesh_1.GroupOnGeom(Top,'Top',SMESH.EDGE)
    Bottom_1 = Mesh_1.GroupOnGeom(Bottom,'Bottom',SMESH.EDGE)
    TopLeft_1 = Mesh_1.GroupOnGeom(TopLeft,'TopLeft',SMESH.FACE)
    BottomLeft_1 = Mesh_1.GroupOnGeom(BottomLeft,'BottomLeft',SMESH.FACE)
    TopRight_1 = Mesh_1.GroupOnGeom(TopRight,'TopRight',SMESH.FACE)
    BottomRight_1 = Mesh_1.GroupOnGeom(BottomRight,'BottomRight',SMESH.FACE)

    Regular_1D_1 = Mesh_1.Segment(geom=TopLeft)
    TopLeft_2 = Regular_1D_1.GetSubMesh()
    TopLeft_3 = Regular_1D_1.NumberOfSegments(600,200,[])
    Quadrangle_2D_1 = Mesh_1.Quadrangle(algo=smeshBuilder.QUADRANGLE,geom=TopLeft)

    Regular_1D_2 = Mesh_1.Segment(geom=BottomLeft)
    BottomLeft_2 = Regular_1D_2.GetSubMesh()
    BottomLeft_3 = Regular_1D_2.NumberOfSegments(600,200,[ 26, 33, 31, 18, 16, 28, 13, 7, 9, 25, 23 ])
    Quadrangle_2D_2 = Mesh_1.Quadrangle(algo=smeshBuilder.QUADRANGLE,geom=BottomLeft)
    isDone = Mesh_1.SetMeshOrder( [ [ TopLeft_2, BottomLeft_2 ] ])

    Regular_1D_3 = Mesh_1.Segment(geom=TopRight)
    TopRight_2 = Regular_1D_3.GetSubMesh()
    TopRight_3 = Regular_1D_3.NumberOfSegments(600,200,[ 20 ])
    Quadrangle_2D_3 = Mesh_1.Quadrangle(algo=smeshBuilder.QUADRANGLE,geom=TopRight)
    isDone = Mesh_1.SetMeshOrder( [ [ TopLeft_2, BottomLeft_2, TopRight_2 ] ])

    Regular_1D_4 = Mesh_1.Segment(geom=BottomRight)
    BottomRight_2 = Regular_1D_4.GetSubMesh()
    BottomRight_3 = Regular_1D_4.NumberOfSegments(600,200,[ 20, 26, 31 ])
    Quadrangle_2D_4 = Mesh_1.Quadrangle(algo=smeshBuilder.QUADRANGLE,geom=BottomRight)
    isDone = Mesh_1.SetMeshOrder( [ [ TopLeft_2, BottomLeft_2, TopRight_2, BottomRight_2 ] ])


    isDone = Mesh_1.Compute()
    [ FarField_extruded, Airfoil_extruded, TopLeft_extruded, BottomLeft_extruded, TopRight_extruded, BottomRight_extruded, FarField_top, Airfoil_top, TopLeft_top, BottomLeft_top, TopRight_top, BottomRight_top ] = Mesh_1.ExtrusionSweepObjects( [], [], [ Mesh_1 ], [ 0, 0, 1 ], 1, 1, [  ], 0, [  ], [  ], 0 )


    ## Set names of Mesh objects
    smesh.SetName(BottomRight_3, 'BottomRight')
    smesh.SetName(TopLeft_3, 'TopLeft')
    smesh.SetName(BottomLeft_3, 'BottomLeft')
    smesh.SetName(TopRight_3, 'TopRight')
    smesh.SetName(BottomRight_top, 'BottomRight_top')
    smesh.SetName(Regular_1D.GetAlgorithm(), 'Regular_1D')
    smesh.SetName(Quadrangle_2D.GetAlgorithm(), 'Quadrangle_2D')
    smesh.SetName(TopRight_top, 'TopRight_top')
    smesh.SetName(BottomLeft_top, 'BottomLeft_top')
    smesh.SetName(BottomRight_extruded, 'BottomRight_extruded')
    smesh.SetName(BottomLeft_extruded, 'BottomLeft_extruded')
    smesh.SetName(TopRight_extruded, 'TopRight_extruded')
    smesh.SetName(TopLeft_1, 'TopLeft')
    smesh.SetName(TopLeft_extruded, 'TopLeft_extruded')
    smesh.SetName(TopRight_1, 'TopRight')
    smesh.SetName(BottomLeft_1, 'BottomLeft')
    smesh.SetName(FarField_extruded, 'FarField_extruded')
    smesh.SetName(BottomRight_1, 'BottomRight')
    smesh.SetName(TopLeft_top, 'TopLeft_top')
    smesh.SetName(Airfoil_top, 'Airfoil_top')
    smesh.SetName(Airfoil_extruded, 'Airfoil_extruded')
    smesh.SetName(Mesh_1.GetMesh(), 'Mesh_1')
    smesh.SetName(FarField_1, 'FarField')
    smesh.SetName(Airfoil_1, 'Airfoil')
    smesh.SetName(Left_1, 'Left')
    smesh.SetName(Right_1, 'Right')
    smesh.SetName(Top_1, 'Top')
    smesh.SetName(Bottom_1, 'Bottom')
    smesh.SetName(FarField_top, 'FarField_top')
    smesh.SetName(BottomLeft_2, 'BottomLeft')
    smesh.SetName(TopLeft_2, 'TopLeft')
    smesh.SetName(Mesh, 'Mesh')
    smesh.SetName(BottomRight_2, 'BottomRight')
    smesh.SetName(TopRight_2, 'TopRight')

    if salome.sg.hasDesktop():
        salome.sg.updateObjBrowser()


    mesh = Mesh_1

    mName=mesh.GetName()
    print("Exporting to " + outdir)       
    salomeToOpenFOAM.exportToFoam(mesh,outdir)
    print("finished exporting\n",1)

def fix_boundary(outdir):
    line_nums = []
    to_change = ['TopLeft', 'BottomLeft', 'TopRight', 'BottomRight', 'TopLeft_top', 'BottomLeft_top', 'TopRight_top', 'BottomRight_top']
    new_file = []

    with open(outdir + '/boundary', 'r') as f:

        for idx, line in enumerate(f.readlines()):

            # if we gonna need to change it
            if line.strip() in to_change:
                line_nums.append(idx+2)

            # save the contents somewhere
            new_file.append(line)

    for idx in line_nums:
        new_file[idx] = '		type		empty;\n'

    # rewrite file
    with open(outdir + '/boundary', 'w') as f:
        f.writelines(new_file)


if __name__ == '__main__': 
    ###
    ### CONTROL POINT EXTRACTION
    ###

    indir = r"C:\Users\Ben Greenberg\Documents\gems\airfoilProject\controlPoints\ControlPoints4415.txt"
    outdir = './base/airfoilOptTest1Clean/constant/polyMesh'
    xC = []
    yC = []
    zC = []
    with open(indir) as f:
        reader = csv.reader(f, delimiter = "\t")
        for n in reader:
            if (n[0] == "START"): #ignore start lines
                pass
            elif (n[0] == "END"): #ignore end lines
                pass
            else:
                xC.append(n[0]) #add first number in each row to x coordinate list
                yC.append(n[1]) #add second number to y list
                zC.append(n[2]) #third to z list
        f.close()

    salome_stuff(xC, yC, zC, outdir=outdir)
    fix_boundary(outdir)