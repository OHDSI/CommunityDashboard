import numpy as np 
from flask import render_template, request, render_template_string, Blueprint
import re
import string

from plots.blueprints import htmlBuilderFunctions
from plots.services import db

transcriptContainer = db.init_cosmos('transcripts')
bp = Blueprint('youtube', __name__)

@bp.route('/transcripts', methods = ['GET'])
def transcripts():

    transcriptID = request.args.get('id', None)
    transcript = ''
    #query item with the search query
    for item in transcriptContainer.query_items( query='SELECT * FROM transcripts WHERE transcripts.id=@id',
            parameters = [{ "name":"@id", "value": transcriptID }], 
            enable_cross_partition_query=True):
        if(item['id'] == request.args.get('id', None)):
            if(item['data'][0]['transcript'] == 'TranscriptsDisabled'):
                transcript = 'Transcripts Disabled. Please check back later...'
            elif((isinstance(item['data'][0]['snomedNames'], type(None)) == False) & \
                (isinstance(item['data'][0]['umlsStartChar'], type(None)) == False) & \
                    ((((list(set(item['data'][0]['snomedNames']))[0] == "No Mapping Found") & (len(list(set(item['data'][0]['snomedNames']))) == 1)) == False)) & \
                        ((((list(set(item['data'][0]['snomedNames']))[0] == 'Sodium-22') & (len(list(set(item['data'][0]['snomedNames']))) == 1)) == False)) ):
                    # (((len(item['data'][0]['snomedNames']) == 1 )& (item['data'][0]['snomedNames'][0] == "No Mapping Found")) == False)):
                # print(list(set(item['data'][0]['snomedNames']))[0])
                #get full transcript
                transcript = item['data'][0]['transcript']

                #identify list of meshterms
                lsTerms = []
                lsOccurenceTimes = []
                umlsTermsLength = len(item['data'][0]['umlsStartChar'])
                for i in range(0, umlsTermsLength):
                    if(item['data'][0]['snomedNames'][i] != "No Mapping Found"):
                        if(item['data'][0]['umlsStartChar'][i] != 'NA'):
                            #extract the string from the transcript based on positions
                            start = int(item['data'][0]['umlsStartChar'][i])
                            end = int(item['data'][0]['umlsEndChar'][i]) - 1
                            targetString = transcript[start:end+1]
                            lsTerms = np.append(lsTerms, targetString)

                #highlight all instances
                for term in lsTerms:
                    transcript = re.sub((term + "|" + term.upper() + "|" + term.lower() + "|" + term.capitalize()), ('<mark>' + term + '</mark>'), transcript)
                
                # print(lsTerms)
                #find all the highlighted instances
                markStart = [i for i in range(len(transcript)) if transcript.startswith("<mark>", i)]
                markEnd = [i + 7 for i in range(len(transcript)) if transcript.startswith("</mark>", i)]
                for i in range(len(markStart)):
                    stringUptoTerm = transcript[0: markStart[i]]
                    #find number of words stripping of punctuations
                    strAsListWords = re.sub('['+string.punctuation+']', '', stringUptoTerm).split()
                    numWords = len(strAsListWords)
                    timeOccurred = "It might be around " + str(int(np.floor(((numWords / 150) * 60) / 60))) + " minute(s)" + " " + \
                                        str(int(np.floor(((numWords / 150) * 60) % 60))) + " second(s) ± 15 seconds"
                    lsOccurenceTimes = np.append(lsOccurenceTimes, timeOccurred)

                #underlilne is faulty
                addedLength = 0
                for i in range(len(markStart)):
                    strBeforeMark = transcript[0:markStart[i] + addedLength]
                    strWithinMark = transcript[markStart[i] + addedLength:markEnd[i] + addedLength]
                    strAfterMark = transcript[markEnd[i] + addedLength:len(transcript)]

                    transcript = strBeforeMark + " <div class='tooltip'> " + strWithinMark + \
                                    " <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span>" + \
                                        " </div> " + strAfterMark
                    addedLength = addedLength + len(" <div class='tooltip'>  <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span> </div> ")


                #occurrence time is faulty
                # for i in range(len(lsTerms)):
                #     pattern = ("<mark>" + lsTerms[i] + "</mark>" + "|" +\
                #                         "<mark>" + lsTerms[i].upper() + "</mark>" + "|" +\
                #                             "<mark>" + lsTerms[i].lower() + "<mark>" + "|" + \
                #                                 "<mark>" + lsTerms[i].capitalize() + "</mark>")
                #     transcript = re.sub(pattern, " <div class='tooltip'> " + ('<mark>' + lsTerms[i] + '</mark>') + \
                #                     " <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span>" + \
                #                         " </div> ", transcript)

                # print(lsOccurenceTimes)
                #fill out the rest of the html codes
                transcript = htmlBuilderFunctions.addTagWrapper(transcript, "body")
                #add style
                tooltipStyle = '<style> \
                                .tooltip { \
                                position: auto; \
                                display: inline-block;\
                                border-bottom: 1px dotted black;\
                                }\
                                .tooltip .tooltiptext {\
                                visibility: hidden;\
                                width: 120px;\
                                background-color: black;\
                                color: #fff;\
                                text-align: center;\
                                border-radius: 6px;\
                                padding: 5px 0;\
                                position: absolute;\
                                z-index: 1;\
                                }\
                                .tooltip:hover .tooltiptext {\
                                visibility: visible;\
                                }\
                                </style>'

                transcript = tooltipStyle + transcript
                transcript = htmlBuilderFunctions.addTagWrapper(transcript, "html")


                # del transcriptID
            else:
                transcript = "No SNOMED Terms Identified"
    if(transcript == ""):
        transcript = "To be updated soon..."
    return render_template_string(str(transcript))


@bp.route('/youtube_dashboard/', methods = ['POST', 'GET'])
def dashboard_youtube():
    return render_template("youtube_dashboard.html")