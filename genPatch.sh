#!/bin/sh

mytop=$(pwd)
logfilename="log.txt"
outputdir="patch_out_tmp"
patchname=""

patchhistory="leopard/build/gs702c/prebuilt/fwmisc/patchs_history"

compress_dir=""

while true ; do
    case "$1" in
        -o) 
            shift 
            outputdir=$1;shift
            ;;

        -n) 
            shift 
            patchname=$1;shift
            ;;

        *) 
            break ;;

    esac
done

startxml=$1
endxml=$2

if [[ $patchname ]]; then
    patchname="${endxml%.*}_${patchname}"
else
    patchname="${endxml%.*}"
fi

#patchname="${patchname}_$(date +%Y%m%d)"
patchoutdir="${outputdir}/${patchname}"
logfile="${patchoutdir}/${logfilename}"

echo "startxml=${startxml}"
echo "endxml=${endxml}"
echo "outputdir=${outputdir}"
echo "patchname=${patchname}"

if [[ "$startxml" = "" ]] ||  [[ "$endxml" = "" ]] ||  [[ "$outputdir" = "" ]]; then
    echo "parameter error"
    exit 1;
fi

if [[ -d  ${patchoutdir} ]]; then
    echo "delete ${patchoutdir}"
    rm -rf ${patchoutdir}
fi
mkdir -p ${outputdir}
mkdir -p ${patchoutdir}

rm -rf ${logfile}
rm -rf "${patchoutdir}/changed_files.txt"
if [[ -d android ]] ; then
    eval python ./repodiff.py -p -r "android" -o "${patchoutdir}/android" -x "${startxml}" "${endxml}" 2>&1 | tee >> ${logfile}

    if [[ -f "${patchoutdir}/android/changed_files.txt" ]] && [[ $(cat "${patchoutdir}/android/changed_files.txt") ]]; then
        echo "Android:" >>  "${patchoutdir}/changed_files.txt"
        cat "${patchoutdir}/android/changed_files.txt" >>  "${patchoutdir}/changed_files.txt"       
        compress_dir="${compress_dir} android"
    fi
    rm "${patchoutdir}/android/changed_files.txt"
fi

if [[ -d leopard ]] ; then
    eval python ./repodiff.py -p -r "leopard" -o "${patchoutdir}/leopard" -x "${startxml}" "${endxml}" 2>&1 | tee >> ${logfile}
    if [[ -f "${patchoutdir}/leopard/changed_files.txt" ]] && [[ $(cat "${patchoutdir}/leopard/changed_files.txt") ]]; then
        echo "" >>  "${patchoutdir}/changed_files.txt"
        echo "Leopard:" >>  "${patchoutdir}/changed_files.txt"
        cat "${patchoutdir}/leopard/changed_files.txt" >>  "${patchoutdir}/changed_files.txt"       
    fi
    rm "${patchoutdir}/leopard/changed_files.txt"  
fi



if [[ -f "${patchoutdir}/changed_files.txt" ]] && [[ $(cat "${patchoutdir}/changed_files.txt") ]]; then
		compress_dir="${compress_dir} leopard"
    mkdir -p "${patchoutdir}/${patchhistory}"
    echo "" > "${patchoutdir}/${patchhistory}/${patchname}.txt"

    echo "build packages..."
    cd ${patchoutdir}
    eval tar -zcf "${patchname}.tar.gz" "${compress_dir}"
    cd ${mytop}
    echo "genpatch success! "
    echo "${patchoutdir}/${patchname}.tar.gz"
else
    echo "nothing changed!"
fi






