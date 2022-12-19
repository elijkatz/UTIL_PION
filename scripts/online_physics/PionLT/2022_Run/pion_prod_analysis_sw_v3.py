#! /usr/bin/python

# 15/01/21 - Stephen Kay, University of Regina
# 21/06/21 - Edited By - Muhammad Junaid, University of Regina, Canada
# 28/11/21 - Version 2 - Utilises new ltsep package by Richard Trotta
# 19/01/22 - Version 3 - adding functionality to automaticly pick the correct MM cut based on entered target type NH

# Python version of the pion analysis script. Now utilises uproot to select event of each type and writes them to a root file
# Intention is to apply PID/selection cutting here and plot in a separate script
# Python should allow for easier reading of databases storing timing offsets e.t.c.
# 27/04/21 - Updated to use new hcana variables, old determinations removed
# 05/10/21 - Updated to add in focal plane quantities (Jacob Murphy)
# 12/10/21 - Added in Dipole Exit quantities (Jacob Murphy)
# 13/10/21 - Added in SHMS Calorimeter Block hits (Jacob Murphy)
# 15/10/21 - Added in eplane and earray values to analysis. Will need to replay again to include new branches to get for analysis
# 26/10/21 - Added in new tree for analysis rootfile that is prompt with MM cuts
# 09/11/21 - SJDK - v2 uses the changes to the python package Richard made, it is now "ltsep" and NOT "kaonlt", these changes are intended
# to make the package more transferable.
# 19/01/22 - NH - v3 adds in the target as an argument that needs to be provided, MM cut range is determined by target type
# SJDK - Might be better for the target to be an "optional" argument, it defaults to LH2 if nothing provided, works for now though
# 05/07/22 - SJDK - Changed naming of P_gtr_xp and P_gtr_yp to P_gtr_xptar and P_gtr_yptar as these are what theta and phi actually correspond to

###################################################################################################################################################

# Import relevant packages
import uproot as up
import numpy as np
import root_numpy as rnp
import pandas as pd
import root_pandas as rpd
import ROOT
import scipy
import scipy.integrate as integrate
import matplotlib.pyplot as plt
import sys, math, os, subprocess

##################################################################################################################################################

# Check the number of arguments provided to the script
if len(sys.argv)-1!=4:
    print("!!!!! ERROR !!!!!\n Expected 4 arguments\n Usage is with - ROOTfilePrefix RunNumber MaxEvents Target\n!!!!! ERROR !!!!!")
    sys.exit(1)

################################################################################################################################################
'''
ltsep package import and pathing definitions
'''

# Import package for cuts
import ltsep as lt 

# Add this to all files for more dynamic pathing
USER =  lt.SetPath(os.path.realpath(__file__)).getPath("USER") # Grab user info for file finding
HOST = lt.SetPath(os.path.realpath(__file__)).getPath("HOST")
REPLAYPATH = lt.SetPath(os.path.realpath(__file__)).getPath("REPLAYPATH")
UTILPATH = lt.SetPath(os.path.realpath(__file__)).getPath("UTILPATH")
ANATYPE = lt.SetPath(os.path.realpath(__file__)).getPath("ANATYPE")

################################################################################################################################################

# Input params - run number and max number of events
ROOTPrefix = sys.argv[1]
runNum = sys.argv[2]
MaxEvent = sys.argv[3]
Target = sys.argv[4]

# SJDK 19/01/22 - Set MM Range based upon target type specified, change ranges here if desired
if Target == "LH2" or Target == "Dummy10cm":
    MMLo=0.9 # Low edge of MM cut
    MMHi=0.98 # High edge of MM cut
elif Target == "LD2":
    print(Target)
    MMLo=0.88
    MMHi=1.04
else:
    print("Target type not specified (or input incorrectly), defaulting to LH2 MM cut range")
    MMLo=0.9
    MMHi=0.98

OUTPATH=UTILPATH+"/OUTPUT/Analysis/PionLT"
rootName =UTILPATH+"/ROOTfiles/Analysis/PionLT/%s_%s_%s.root" % (ROOTPrefix, runNum, MaxEvent) # Input replay file path

print("Running as %s on %s, hallc_replay_lt path assumed as %s" % (USER, HOST, REPLAYPATH))
print ("Attempting to process %s" %(rootName))
lt.SetPath(os.path.realpath(__file__)).checkDir(OUTPATH)
lt.SetPath(os.path.realpath(__file__)).checkFile(rootName)
print("Output path checks out, outputting to %s" % (OUTPATH))

###############################################################################################################################################

# Read stuff from the main event tree
e_tree = up.open(rootName)["T"]

# Timing info
CTime_ePiCoinTime_ROC1 = e_tree.array("CTime.ePiCoinTime_ROC1")  #
CTime_eKCoinTime_ROC1 = e_tree.array("CTime.eKCoinTime_ROC1")    #
CTime_epCoinTime_ROC1 = e_tree.array("CTime.epCoinTime_ROC1")    #
H_RF_Dist = e_tree.array("RFTime.HMS_RFtimeDist")            #
P_RF_Dist = e_tree.array("RFTime.SHMS_RFtimeDist")           #

# HMS info
H_hod_goodscinhit = e_tree.array("H.hod.goodscinhit")            #
H_hod_goodstarttime = e_tree.array("H.hod.goodstarttime")        #
H_gtr_beta = e_tree.array("H.gtr.beta")                          # Beta is velocity of particle between pairs of hodoscopes
H_gtr_xp = e_tree.array("H.gtr.th")                              # xpfp -> Theta
H_gtr_yp = e_tree.array("H.gtr.ph")                              # ypfp -> Phi
H_gtr_dp = e_tree.array("H.gtr.dp")                              # dp is Delta
# JM 05/10/21 Adding in focal plane variables
H_dc_xfp = e_tree.array("H.dc.x_fp")                            # xp is x focal plane, the vertical position in the focal plane
H_dc_xpfp = e_tree.array("H.dc.xp_fp")                          # xpfp is x' focal plane, the vertical angle
H_dc_yfp = e_tree.array("H.dc.y_fp")                            # yp is x focal plane, the vertical position in the focal plane
H_dc_ypfp = e_tree.array("H.dc.yp_fp")                          # ypfp is y' focal plane, the vertical angle
H_cal_etotnorm = e_tree.array("H.cal.etotnorm")                  #
H_cal_etottracknorm = e_tree.array("H.cal.etottracknorm")        #
H_cer_npeSum = e_tree.array("H.cer.npeSum")                      #

# JM 12/10/21 Added in dipole exit variables
H_dc_InsideDipoleExit = e_tree.array("H.dc.InsideDipoleExit")    #
P_dc_InsideDipoleExit = e_tree.array("P.dc.InsideDipoleExit")    #

# SHMS info
P_hod_goodscinhit = e_tree.array("P.hod.goodscinhit")            #
P_hod_goodstarttime = e_tree.array("P.hod.goodstarttime")        #
P_gtr_beta = e_tree.array("P.gtr.beta")                          # Beta is velocity of particle between pairs of hodoscopes
P_gtr_xptar = e_tree.array("P.gtr.th")                           # xptar -> Theta
P_gtr_yptar = e_tree.array("P.gtr.ph")                           # yptar -> Phi
P_gtr_p = e_tree.array("P.gtr.p")                                #
P_gtr_dp = e_tree.array("P.gtr.dp")                              # dp is Delta 
# JM 05/10/21 Added in focal plane variables
P_dc_xfp = e_tree.array("P.dc.x_fp")                             # xp is x focal plane, the vertical position in the focal plane
P_dc_xpfp = e_tree.array("P.dc.xp_fp")                           # xpfp is x' focal plane, the vertical angle
P_dc_yfp = e_tree.array("P.dc.y_fp")                             # yp is x focal plane, the vertical position in the focal plane
P_dc_ypfp = e_tree.array("P.dc.yp_fp")                           # ypfp is y' focal plane, the vertical angle
P_cal_etotnorm = e_tree.array("P.cal.etotnorm")                  #
P_cal_etottracknorm = e_tree.array("P.cal.etottracknorm")        #
P_cal_fly_earray = e_tree.array("P.cal.fly.earray")              #
P_cal_pr_eplane = e_tree.array("P.cal.pr.eplane")                #
# SJDK 13/10/21 - This seems to generate something of type "jagged.array", I suspect it is an indexed array and we can't access it in the same way we access other variables
P_cal_fly_numGoodAdcHits = e_tree.array("P.cal.fly.numGoodAdcHits")# Indexed hits into calorimeter blocks 
# JM 16/10/21 - SJDK's proposed stop-gap for calo hits per block. Summing over total ADC hits per event
# This means we lose calo block position info, but it works in our script right now, so it is at least something
Cal_Adc_Hits = np.empty(len(P_cal_fly_numGoodAdcHits))
for i in range(len(P_cal_fly_numGoodAdcHits)):
    for j in range(224):
        Cal_Adc_Hits[i] += P_cal_fly_numGoodAdcHits[i][j]        # Sum of total ADC hits per event
P_aero_npeSum = e_tree.array("P.aero.npeSum")                    #
P_aero_xAtAero = e_tree.array("P.aero.xAtAero")                  #
P_aero_yAtAero = e_tree.array("P.aero.yAtAero")                  #
P_hgcer_npeSum = e_tree.array("P.hgcer.npeSum")                  #
P_hgcer_xAtCer = e_tree.array("P.hgcer.xAtCer")                  #
P_hgcer_yAtCer = e_tree.array("P.hgcer.yAtCer")                  #
P_ngcer_npeSum = e_tree.array("P.ngcer.npeSum")                  #
P_ngcer_xAtCer = e_tree.array("P.ngcer.xAtCer")                  #
P_ngcer_yAtCer = e_tree.array("P.ngcer.yAtCer")                  #

#Specific Data (Eli)
H_hod_1x_TrackXpos = e_tree.array("H.hod.1x.TrackXPos")
H_hod_1x_TrackYPos = e_tree.array("H.hod.1x.TrackYPos")
H_hod_1x_ScinXPos = e_tree.array("H.hod.1x.ScinXPos")
H_hod_1x_ScinYPos = e_tree.array("H.hod.1x.ScinYPos")
P_dc_1u1_time = e_tree.array("P.dc.1u1.time")
P_dc_1u1_dist =  e_tree.array("P.dc.1u1.dist")
P_dc_1u1_nhit = e_tree.array("P.dc.1u1.nhit")
H_hod_1y_ScinXPos = e_tree.array("H.hod.1y.ScinXPos")
H_hod_1y_ScinYPos = e_tree.array("H.hod.1y.ScinYPos")
H_hod_1y_TrackXPos = e_tree.array("H.hod.1y.TrackXPos")
H_hod_1y_TrackYPos = e_tree.array("H.hod.1y.TrackYPos")

#H_cer_numAdcHits =  e_tree.array("H.cer.numAdcHits")
#H_cer_totNumAdcHits = e_tree.array("H.cer.totNumAdcHits")
#H_cer_adcPedRaw = e_tree.array("H.cer.adcPedRaw")
#H_cer_adcPulseIntRaw = e_tree.array("H.cer.adcPulseIntRaw")
#H_cer_adcPulseAmpRaw = e_tree.array("H.cer.adcPulseAmpRaw")
#H_cer_adcPulseTimeRaw = e_tree.array("H.cer.adcPulseTimeRaw")
#H_cer_adcPed = e_tree.array("H.cer.adcPed")
#H_cer_adcPulseInt = e_tree.array("H.cer.adcPulseInt")
#H_cer_adcPulseAmp = e_tree.array("H.cer.adcPulseAmp")
#H_cer_adcPulseTime = e_tree.array("H.cer.adcPulseTime")
#H_cer_adcSampPedRaw = e_tree.array("H.cer.adcSampPedRaw")
#H_cer_adcSampPulseIntRaw = e_tree.array("H.cer.adcSampPulseIntRaw")
#H_cer_adcSampPulseAmpRaw = e_tree.array("H.cer.adcSampPulseAmpRaw")
#H_cer_adcSampPulseTimeRaw = e_tree.array("H.cer.adcSampPulseTimeRaw")
#H_cer_adcSampPed = e_tree.array("H.cer.adcSampPed")
#H_cer_adcSampPulseInt = e_tree.array("H.cer.adcSampPulseInt")
#H_cer_adcSampPulseAmp =e_tree.array("H.cer.adcSampPulseAmp")
#H_cer_adcSampPulseTime = e_tree.array("H.cer.adcSampPulseTime")
#H_cer_adcCounter = e_tree.array("H.cer.adcCounter")
#H_cer_adcSampleCounter = e_tree.array("H.cer.adcSampleCounter")
#H_cer_adcErrorFlag = e_tree.array("H.cer.adcErrorFlag")
#H_cer_numGoodAdcHits = e_tree.array("H.cer.numGoodAdcHits")
#H_cer_totNumGoodAdcHits = e_tree.array("H.cer.totNumGoodAdcHits")
#H_cer_numTracksMatched = e_tree.array("H.cer.numTracksMatched")
#H_cer_numTracksFired = e_tree.array("H.cer.numTracksFired")
#H_cer_totNumTracksMatched = e_tree.array("H.cer.totNumTracksMatched")
#H_cer_totNumTracksFired = e_tree.array("H.cer.totNumTracksFired")
H_cer_xAtCer = e_tree.array("H.cer.xAtCer")
H_cer_yAtCer = e_tree.array("H.cer.yAtCer")
H_cer_npe = e_tree.array("H.cer.npe")
#H_cer_npeSum = e_tree.array("H.cer.npeSum")
#H_cer_goodAdcPed = e_tree.array("H.cer.goodAdcPed")
#H_cer_goodAdcMult = e_tree.array("H.cer.goodAdcMult")
#H_cer_goodAdcHitUsed = e_tree.array("H.cer.goodAdcHitUsed")
#H_cer_goodAdcPulseInt = e_tree.array("H.cer.goodAdcPulseInt")
#H_cer_goodAdcPulseIntRaw = e_tree.array("H.cer.goodAdcPulseIntRaw")
#H_cer_goodAdcPulseAmp = e_tree.array("H.cer.goodAdcPulseAmp")
#H_cer_goodAdcPulseTime = e_tree.array("H.cer.goodAdcPulseTime")
#H_cer_goodAdcTdcDiffTime = e_tree.array("H.cer.goodAdcTdcDiffTime")
#H_cer_RefTime = e_tree.array("H.cer.RefTime")


np.savetxt("H_hod_1x_TrackXpos.txt", H_hod_1x_TrackXpos)
np.savetxt("H_hod_1x_TrackYPos.txt", H_hod_1x_TrackYPos)
np.savetxt("H_hod_1x_ScinXPos.txt", H_hod_1x_ScinXPos)
np.savetxt("H_hod_1x_ScinYPos.txt", H_hod_1x_ScinYPos)
np.savetxt("P_dc_1u1_time.txt", P_dc_1u1_time)
np.savetxt("P_dc_1u1_dist.txt", P_dc_1u1_dist)
np.savetxt("P_dc_1u1_nhit.txt", P_dc_1u1_nhit)
np.savetxt("H_hod_1y_ScinXPos.txt", H_hod_1y_ScinXPos)
np.savetxt("H_hod_1y_ScinYPos.txt", H_hod_1y_ScinYPos)
np.savetxt("H_hod_1y_TrackXPos.txt", H_hod_1y_TrackXPos)
np.savetxt("H_hod_1y_TrackYPos.txt", H_hod_1y_TrackYPos)
np.savetxt("H_gtr_dp.txt", H_gtr_dp)
np.savetxt("H_cal_etotnorm.txt", H_cal_etotnorm)
np.savetxt("H_cal_etottracknorm.txt", H_cal_etottracknorm)

#np.savetxt("H_cer_numAdcHits.txt", H_cer_numAdcHits)
#np.savetxt("H_cer_totNumAdcHits.txt", H_cer_totNumAdcHits)
#np.savetxt("H_cer_adcPedRaw.txt", H_cer_adcPedRaw)
#np.savetxt("H_cer_adcPulseIntRaw.txt", H_cer_adcPulseIntRaw)
#np.savetxt("H_cer_adcPulseAmpRaw.txt", H_cer_adcPulseAmpRaw)
#np.savetxt("H_cer_adcPulseTimeRaw.txt", H_cer_adcPulseTimeRaw)
#np.savetxt("H_cer_adcPed.txt", H_cer_adcPed)
#np.savetxt("H_cer_adcPulseInt.txt", H_cer_adcPulseInt)
#np.savetxt("H_cer_adcPulseAmp.txt", H_cer_adcPulseAmp)
#np.savetxt("H_cer_adcPulseTime.txt", H_cer_adcPulseTime)
#np.savetxt("H_cer_adcSampPedRaw.txt", H_cer_adcSampPedRaw)
#np.savetxt("H_cer_adcSampPulseIntRaw.txt", H_cer_adcSampPulseIntRaw)
#np.savetxt("H_cer_adcSampPulseAmpRaw.txt", H_cer_adcSampPulseAmpRaw)
#np.savetxt("H_cer_adcSampPulseTimeRaw.txt", H_cer_adcSampPulseTimeRaw)
#np.savetxt("H_cer_adcSampPed.txt", H_cer_adcSampPed)
#np.savetxt("H_cer_adcSampPulseInt.txt", H_cer_adcSampPulseInt)
#np.savetxt("H_cer_adcSampPulseAmp.txt", H_cer_adcSampPulseAmp)
#np.savetxt("H_cer_adcSampPulseTime.txt", H_cer_adcSampPulseTime)
#np.savetxt("H_cer_adcCounter.txt", H_cer_adcCounter)
#np.savetxt("H_cer_adcSampleCounter.txt", H_cer_adcSampleCounter)
#np.savetxt("H_cer_adcErrorFlag.txt", H_cer_adcErrorFlag)
#np.savetxt("H_cer_numGoodAdcHits.txt", H_cer_numGoodAdcHits)
#np.savetxt("H_cer_totNumGoodAdcHits.txt", H_cer_totNumGoodAdcHits)
#np.savetxt("H_cer_numTracksMatched.txt", H_cer_numTracksMatched)
#np.savetxt("H_cer_numTracksFired.txt", H_cer_numTracksFired)
#np.savetxt("H_cer_totNumTracksMatched.txt", H_cer_totNumTracksMatched)
#np.savetxt("H_cer_totNumTracksFired.txt", H_cer_totNumTracksFired)
np.savetxt("H_cer_xAtCer.txt", H_cer_xAtCer)
np.savetxt("H_cer_yAtCer.txt", H_cer_yAtCer)
np.savetxt("H_cer_npe.txt", H_cer_npe)
np.savetxt("H_cer_npeSum.txt", H_cer_npeSum)
#np.savetxt("H_cer_goodAdcPed.txt", H_cer_goodAdcPed)
#np.savetxt("H_cer_goodAdcMult.txt", H_cer_goodAdcMult)
#np.savetxt("H_cer_goodAdcHitUsed.txt", H_cer_goodAdcHitUsed)
#np.savetxt("H_cer_goodAdcPulseInt.txt", H_cer_goodAdcPulseInt)
#np.savetxt("H_cer_goodAdcPulseIntRaw.txt", H_cer_goodAdcPulseIntRaw)
#np.savetxt("H_cer_goodAdcPulseAmp.txt", H_cer_goodAdcPulseAmp)
#np.savetxt("H_cer_goodAdcPulseTime.txt", H_cer_goodAdcPulseTime)
#np.savetxt("H_cer_goodAdcTdcDiffTime.txt", H_cer_goodAdcTdcDiffTime)
#np.savetxt("H_cer_RefTime.txt", H_cer_RefTime)



# Kinematic quantitites
Q2 = e_tree.array("H.kin.primary.Q2")                            #
W = e_tree.array("H.kin.primary.W")                              #
epsilon = e_tree.array("H.kin.primary.epsilon")                  #
th_q = e_tree.array("P.kin.secondary.th_xq")                     # SJDK - 02/11/21 - Added theta for the q vector to the output file
ph_q = e_tree.array("P.kin.secondary.ph_xq")                     #
MMpi = e_tree.array("P.kin.secondary.MMpi")                      #
MMK = e_tree.array("P.kin.secondary.MMK")                        #
MMp = e_tree.array("P.kin.secondary.MMp")                        #
MandelT = e_tree.array("P.kin.secondary.MandelT")                #
#MandelU = e_tree.array("P.kin.secondary.MandelU")               #

# Misc quantities
#fEvtType = e_tree.array("fEvtHdr.fEvtType")                     #
#RFFreq = e_tree.array("MOFC1FREQ")                              #
#RFFreqDiff = e_tree.array("MOFC1DELTA")                         #
#pEDTM = e_tree.array("T.coin.pEDTM_tdcTime")                    #
# Relevant branches now stored as NP arrays

# Define distances from focal plane (cm)
D_Calo = 292.64
D_Exit = -307.0

# Calculate X and Y Positions along tracks from focal plane

xCalo = np.array([xfp+xpfp*D_Calo for (xfp, xpfp) in zip(P_dc_xfp, P_dc_xpfp)])
yCalo = np.array([yfp+ypfp*D_Calo for (yfp, ypfp) in zip(P_dc_yfp, P_dc_ypfp)])
xExit = np.array([xfp+xpfp*D_Exit for (xfp, xpfp) in zip(P_dc_xfp, P_dc_xpfp)])
yExit = np.array([yfp+ypfp*D_Exit for (yfp, ypfp) in zip(P_dc_yfp, P_dc_ypfp)])

# Unindex Calo Hits

##############################################################################################################################################
# SJDK 09/11/21 - New method of adding cuts implemented using ltsep package

# Defining path for cut file
fout = UTILPATH+"/DB/CUTS/run_type/coin_prod.cuts"

# defining Cuts
cuts = ["coin_epi_cut_all_noRF","coin_epi_cut_all_RF","coin_epi_cut_prompt_RF","coin_epi_cut_rand_RF",] # SJDK 01/11/21 - New list of cuts

# read in cuts file and make dictionary
cutVals =[]

def make_cutDict(cuts,fout,runNum,CURRENT_ENV):
    '''
    This method calls several methods in kaonlt package. It is required to create properly formated
    dictionaries. The evaluation must be in the analysis script because the analysis variables (i.e. the
    leaves of interest) are not defined in the kaonlt package. This makes the system more flexible
    overall, but a bit more cumbersome in the analysis script. Perhaps one day a better solution will be
    implimented.
    '''

    # read in cuts file and make dictionary
    importDict = lt.SetCuts(CURRENT_ENV).importDict(cuts,fout,runNum)
    for i,cut in enumerate(cuts):
        x = lt.SetCuts(CURRENT_ENV,importDict).booleanDict(cut)
        #######################################################################################
        # Make list of cut strings
        cutVals.append(x)
        print("\n%s" % cut)
        print(x, "\n")
        if i == 0:
            inputDict = {}
        cutDict = lt.SetCuts(CURRENT_ENV,importDict).readDict(cut,inputDict)
        for j,val in enumerate(x):
            cutDict = lt.SetCuts(CURRENT_ENV,importDict).evalDict(cut,eval(x[j]),cutDict)
    return lt.SetCuts(CURRENT_ENV,cutDict)

c = make_cutDict(cuts,fout,runNum,os.path.realpath(__file__))

#################################################################################################################################################################

def coin_pions(): 
    # Define the array of arrays containing the relevant HMS and SHMS info
    NoCut_COIN_Pions = [H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT]
    Uncut_COIN_Pions = [(H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) for (H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) in zip(*NoCut_COIN_Pions)] 

    # Create array of arrays of pions after cuts, all events, prompt and random
    Cut_COIN_Pions_tmp = NoCut_COIN_Pions
    Cut_COIN_Pions_noRF_tmp = []
    Cut_COIN_Pions_all_tmp = []
    Cut_COIN_Pions_prompt_tmp = []
    Cut_COIN_Pions_prompt_MM_tmp = []
    Cut_COIN_Pions_rand_tmp = []

    for arr in Cut_COIN_Pions_tmp:
        Cut_COIN_Pions_noRF_tmp.append(c.add_cut(arr, "coin_epi_cut_all_noRF"))
        Cut_COIN_Pions_all_tmp.append(c.add_cut(arr, "coin_epi_cut_all_RF"))
        Cut_COIN_Pions_prompt_tmp.append(c.add_cut(arr, "coin_epi_cut_prompt_RF"))
        Cut_COIN_Pions_prompt_MM_tmp.append(c.add_cut(arr, "coin_epi_cut_prompt_RF"))
        Cut_COIN_Pions_rand_tmp.append(c.add_cut(arr, "coin_epi_cut_rand_RF"))

    Cut_COIN_Pions_noRF = [(H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) for (H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) in zip(*Cut_COIN_Pions_noRF_tmp)
        ]

    Cut_COIN_Pions_all = [(H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) for (H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) in zip(*Cut_COIN_Pions_all_tmp)
	]

    Cut_COIN_Pions_prompt = [(H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) for (H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) in zip(*Cut_COIN_Pions_prompt_tmp)
        ]
    # 19/01/22 - NH - added if statment to auto change these cut ranges that stephen was doing manually before.
    # 19/01/22 - SJDK - Tweaked this so that the values are set higher up, saves duplicating a huge block here
    Cut_COIN_Pions_prompt_MM = [(H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) for (H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) in zip(*Cut_COIN_Pions_prompt_MM_tmp)
       if MMpi < MMHi and MMpi > MMLo ]

    Cut_COIN_Pions_random = [(H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) for (H_gtr_beta, H_gtr_xp, H_gtr_yp, H_gtr_dp, H_dc_xfp, H_dc_xpfp, H_dc_yfp, H_dc_ypfp, H_hod_goodscinhit, H_hod_goodstarttime, H_cal_etotnorm, H_cal_etottracknorm, H_cer_npeSum, H_dc_InsideDipoleExit, P_dc_InsideDipoleExit, CTime_ePiCoinTime_ROC1, P_gtr_beta, P_gtr_xptar, P_gtr_yptar, P_gtr_p, P_gtr_dp, P_dc_xfp, P_dc_xpfp, P_dc_yfp, P_dc_ypfp, P_hod_goodscinhit, P_hod_goodstarttime, P_cal_etotnorm, P_cal_etottracknorm, P_cal_fly_earray, P_cal_pr_eplane, Cal_Adc_Hits, P_aero_npeSum, P_aero_xAtAero, P_aero_yAtAero, P_hgcer_npeSum, P_hgcer_xAtCer, P_hgcer_yAtCer, P_ngcer_npeSum, P_ngcer_xAtCer, P_ngcer_yAtCer, MMpi, H_RF_Dist, P_RF_Dist, xCalo, yCalo, xExit, yExit, Q2, W, epsilon, th_q, ph_q, MandelT) in zip(*Cut_COIN_Pions_rand_tmp)
        ]

    COIN_Pions = {
        "Uncut_Pion_Events" : Uncut_COIN_Pions,
        "Cut_Pion_Events_noRF" : Cut_COIN_Pions_noRF,
        "Cut_Pion_Events_All" : Cut_COIN_Pions_all,
        "Cut_Pion_Events_Prompt" : Cut_COIN_Pions_prompt,
        "Cut_Pion_Events_Prompt_MM" : Cut_COIN_Pions_prompt_MM,
        "Cut_Pion_Events_Random" : Cut_COIN_Pions_random,
        }

    return COIN_Pions

#################################################################################################################################################################

def main():
    COIN_Pion_Data = coin_pions()

    # This is just the list of branches we use from the initial root file for each dict
    # I don't like re-defining this here as it's very prone to errors if you included (or removed something) earlier but didn't modify it here
    # Should base the branches to include based on some list and just repeat the list here (or call it again directly below)

    COIN_Pion_Data_Header = ["H_gtr_beta","H_gtr_xp","H_gtr_yp","H_gtr_dp","H_dc_xfp", "H_dc_xpfp", "H_dc_yfp", "H_dc_ypfp","H_hod_goodscinhit","H_hod_goodstarttime","H_cal_etotnorm","H_cal_etottracknorm","H_cer_npeSum","H_dc_InsideDipoleExit","P_dc_InsideDipoleExit","CTime_ePiCoinTime_ROC1","P_gtr_beta","P_gtr_xptar","P_gtr_yptar","P_gtr_p","P_gtr_dp","P_dc_xfp", "P_dc_xpfp", "P_dc_yfp", "P_dc_ypfp","P_hod_goodscinhit","P_hod_goodstarttime","P_cal_etotnorm","P_cal_etottracknorm","P_cal_fly_earray","P_cal_pr_eplane","Cal_Adc_Hits","P_aero_npeSum","P_aero_xAtAero","P_aero_yAtAero","P_hgcer_npeSum","P_hgcer_xAtCer","P_hgcer_yAtCer","P_ngcer_npeSum","P_ngcer_xAtCer","P_ngcer_yAtCer","MMpi","H_RF_Dist","P_RF_Dist","xCalo","yCalo","xExit","yExit","Q2","W","epsilon","th_q","ph_q","MandelT"]

    # Need to create a dict for all the branches we grab
    data = {}
    data.update(COIN_Pion_Data)
    data_keys = list(data.keys()) # Create a list of all the keys in all dicts added above, each is an array of data

    for i in range (0, len(data_keys)):
        if("Pion" in data_keys[i]):
            DFHeader=list(COIN_Pion_Data_Header)
        else:
            continue
            # Uncomment the line below if you want .csv file output, WARNING the files can be very large and take a long time to process!
            #pd.DataFrame(data.get(data_keys[i])).to_csv("%s/%s_%s.csv" % (OUTPATH, data_keys[i], runNum), header=DFHeader, index=False) # Convert array to panda dataframe and write to csv with correct header
        if (i == 0):
            pd.DataFrame(data.get(data_keys[i]), columns = DFHeader, index = None).to_root("%s/%s_%s_Analysed_Data.root" % (OUTPATH, runNum, MaxEvent), key ="%s" % data_keys[i])
        elif (i != 0):
            pd.DataFrame(data.get(data_keys[i]), columns = DFHeader, index = None).to_root("%s/%s_%s_Analysed_Data.root" % (OUTPATH, runNum, MaxEvent), key ="%s" % data_keys[i], mode ='a') 
                    
if __name__ == '__main__':
    main()
print ("Processing Complete")
