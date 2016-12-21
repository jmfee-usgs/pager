import os
import copy
from  datetime import datetime
from impactutils.time.timeutils import get_local_time
from impactutils.textformat.text import pop_round_short
from impactutils.textformat.text import dec_to_roman
from impactutils.colors.cpalette import ColorPalette
from impactutils.comcat.query import ComCatInfo
from impactutils.io.cmd import get_command_output
import numpy as np

from losspager.io.pagerdata import PagerData

LATEX_TO_PDF_BIN = 'pdflatex'

def create_onepager(version_dir, debug = False):
    """
    :param version_dir: 
      Path of event version directory.
    :param debug:
      bool for whether or not to add textpos boxes to onepager.
    """

    #---------------------------------------------------------------------------
    # Sort out some paths
    #---------------------------------------------------------------------------

    # Locaiton of this module
    mod_dir, dummy = os.path.split(__file__)

    # losspager package direcotry
    losspager_dir = os.path.join(mod_dir, '..')

    # Repository root directory
    root_dir = os.path.join(losspager_dir, '..')

    # Data directory
    data_dir = os.path.join(losspager_dir, 'data')

    # Onepager latex template file
    template_file = os.path.join(data_dir, 'onepager2.tex')

    #---------------------------------------------------------------------------
    # Read in pager data and latex template
    #---------------------------------------------------------------------------

    json_dir = os.path.join(version_dir, 'json')
    pdata = PagerData()
    pdata.loadFromJSON(json_dir)
    pdict = copy.deepcopy(pdata._pagerdict)
    edict = pdata.getEventInfo()
    
    with open(template_file, 'r') as f:
        template = f.read()

    #---------------------------------------------------------------------------
    # Fill in template values
    #---------------------------------------------------------------------------

    # Sort out origin time
    olat = edict['lat']
    olon = edict['lon']
    otime_utc = edict['time']
    date_utc = datetime.strptime(otime_utc, "%Y-%m-%d %H:%M:%S")
    date_local = get_local_time(date_utc, olat, olon)
    DoW = date_local.strftime('%a')
    otime_local = date_local.strftime('%H:%M:%S')
    otime_local = DoW + ' ' + otime_local
    template = template.replace("[ORIGTIME]", otime_utc)
    template = template.replace("[LOCALTIME]", otime_local)

    # Some paths
    template = template.replace("[VERSIONFOLDER]", version_dir)
    template = template.replace("[HOMEDIR]", root_dir)

    # Magnitude location string under USGS logo
    magloc = "M " + str(edict['mag']) + ", " + \
        edict['location']
    template = template.replace("[MAGLOC]", magloc)

    # Pager version
    ver = "Version " + str(pdict['pager']['version_number'])
    template = template.replace("[VERSION]", ver)
    template = template.replace("[VERSIONX]", "2.5")

    # Epicenter location
    lat = edict['lat']
    lon = edict['lon']
    dep = edict['depth']
    if lat > 0:
        hlat = "N"
    else:
        hlat = "S"
    if lon > 0:
        hlon = "E"
    else:
        hlon = "W"
    template = template.replace("[LAT]", str(abs(lat)))
    template = template.replace("[LON]", str(abs(lon)))
    template = template.replace("[HEMILAT]", str(hlat))
    template = template.replace("[HEMILON]", str(hlon))
    template = template.replace("[DEPTH]", str(dep))

    # Tsunami warning? --- need to fix to be a function of tsunamic flag
    if edict['tsunami']:
        template = template.replace("[TSUNAMI]", "FOR TSUNAMI INFORMATION, SEE: tsunami.gov")
    else:
        template = template.replace("[TSUNAMI]", "")
    elapse = "Created: " + pdict['pager']['elapsed_time'] + " after earthquake"
    template = template.replace("[ELAPSED]", elapse)
    template = template.replace(
        "[IMPACT1]", pdict['comments']['impact1'].replace("%", "\%"))
    template = template.replace(
        "[IMPACT2]", pdict['comments']['impact2'].replace("%", "\%"))
    template = template.replace(
        "[STRUCTCOMMENT]", pdict['comments']['struct_comment'].replace("%", "\%"))

    # Fill in exposure values
    mmi = np.array(pdict['population_exposure']['mmi'])
    exp = np.array(pdict['population_exposure']['aggregated_exposure'])
    cum_exp = np.cumsum(exp)
    not_covered = cum_exp == 0
    template = template.replace("[MMI]", "MMI")
    if not_covered[0] == True:
        mmi1 = '--*'
    else:
        mmi1 = pop_round_short(exp[mmi == 1][0])
    template = template.replace("[MMI1]", mmi1)
    if not_covered[2] == True:
        mmi23 = '--*'
    else:
        mmi23 = pop_round_short(np.sum(exp[(mmi == 2) | (mmi == 3)]))
    template = template.replace("[MMI2-3]", mmi23)
    if not_covered[3] == True:
        mmi4 = '--*'
    else:
        mmi4 = pop_round_short(exp[mmi == 4][0])
    template = template.replace("[MMI4]", mmi4)
    if not_covered[4] == True:
        mmi5 = '--*'
    else:
        mmi5 = pop_round_short(exp[mmi == 5][0])
    template = template.replace("[MMI5]", mmi5)
    template = template.replace("[MMI6]", pop_round_short(exp[mmi == 6][0]))
    template = template.replace("[MMI7]", pop_round_short(exp[mmi == 7][0]))
    template = template.replace("[MMI8]", pop_round_short(exp[mmi == 8][0]))
    template = template.replace("[MMI9]", pop_round_short(exp[mmi == 9][0]))
    template = template.replace("[MMI10]", pop_round_short(exp[mmi == 10][0]))

    # MMI color pal
    pal = ColorPalette.fromPreset('mmi')

    # Historical table
    htab = pdata.getHistoricalTable()
    if htab[0] is None:
        # use pdata.getHistoricalComment()
        htex = pdata.getHistoricalComment()
    else:
        # build latex table
        htex = """
\\begin{tabularx}{7.25cm}{lrc*{1}{>{\\centering\\arraybackslash}X}r}
\hline
\\textbf{Date} &\\textbf{Dist.}&\\textbf{Mag.}&\\textbf{Max}    &\\textbf{Shaking}\\\\
\\textbf{(UTC)}&\\textbf{(km)} &              &\\textbf{MMI(\#)}&\\textbf{Deaths} \\\\
\hline
[TABLEDATA]
\hline
\multicolumn{5}{p{7.2cm}}{\\raggedright \\footnotesize [COMMENT]}
\end{tabularx}"""
        comment = pdata._pagerdict['comments']['secondary_comment']
        htex = htex.replace("[COMMENT]", comment)
        tabledata = ""
        nrows = len(htab)
        for i in range(nrows):
            date = htab[i]['Time'].split()[0]
            dist = str(int(htab[i]['Distance']))
            mag = str(htab[i]['Magnitude'])
            mmi = dec_to_roman(np.round(htab[i]['MaxMMI'], 0))
            col = pal.getDataColor(htab[i]['MaxMMI'])
            texcol = "%s,%s,%s" %(col[0], col[1], col[2])
            nmmi = pop_round_short(htab[i]['NumMaxMMI'])
            mmicell = '%s(%s)' %(mmi, nmmi)
            shakedeath = htab[i]['ShakingDeaths']
            if np.isnan(shakedeath):
                death = "--"
            else:
                death = pop_round_short(shakedeath)
            row = '%s & %s & %s & \cellcolor[rgb]{%s} %s & %s \\\\ '\
                  '\n' %(date, dist, mag, texcol, mmicell, death)
            tabledata = tabledata + row
        htex = htex.replace("[TABLEDATA]", tabledata)
    template = template.replace("[HISTORICAL_BLOCK]", htex)

    # City table
    ctex = """
\\begin{tabularx}{7.25cm}{lXr}
\hline
\\textbf{MMI} & \\textbf{City} & \\textbf{Population}  \\\\
\hline
[TABLEDATA]
\hline
\end{tabularx}"""
    ctab = pdata.getCityTable()
    nrows = len(ctab.index)
    tabledata = ""
    for i in range(nrows):
        mmi = dec_to_roman(np.round(ctab['mmi'][i], 0))
        city = ctab['name'][i]
        pop = pop_round_short(ctab['pop'][i])
        col = pal.getDataColor(ctab['mmi'][i])
        texcol = "%s,%s,%s" %(col[0], col[1], col[2])
        if ctab['on_map'][i] == 1:
            row = '\\rowcolor[rgb]{%s}\\textbf{%s} & \\textbf{%s} & '\
                  '\\textbf{%s}\\\\ \n' %(texcol, mmi, city, pop)
        else:
            row = '\\rowcolor[rgb]{%s}%s & %s & '\
                  '%s\\\\ \n' %(texcol, mmi, city, pop)
        tabledata = tabledata + row
    ctex = ctex.replace("[TABLEDATA]", tabledata)
    template = template.replace("[CITYTABLE]", ctex)


    eventid = edict['eventid']
#    test = ComCatInfo(eventid) # cannot connect; will if 'ci' is prepended.

    eventid = "Event ID: " + eventid
    template = template.replace("[EVENTID]", eventid)

    # Write latex file
    tex_output = os.path.join(version_dir, 'onepager.tex')
    with open(tex_output, 'w') as f:
        f.write(template)

    pdf_output = os.path.join(version_dir, 'onepager.pdf')
    stderr = ''
    try:
        cwd = os.getcwd()
        os.chdir(version_dir)
        cmd = '%s -interaction nonstopmode %s' % (LATEX_TO_PDF_BIN,tex_output)
        print('Running %s...' % cmd)
        res,stdout,stderr = get_command_output(cmd)
        os.chdir(cwd)
        if not res:
            return (None,stderr)
        else:
            if os.path.isfile(pdf_output):
                return (pdf_output,stderr)
            else:
                pass
    except Exception as e:
        pass
    finally:
        os.chdir(cwd)
    return (None,stderr)
