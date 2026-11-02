! Patch 0002 regression, reduced from PhiWeather module_channel_routing.F90,
! drive_channel (original QLINK(i,1)=DIFFUSION at lines 1050-1052).
! Compile-only: unresolved external procedures deliberately retain call pressure.
! Imported process IDs remain module variables; no external modules are needed.
! Keep the surrounding routing branches and array descriptors: reducing pressure
! can let the index pseudo get a hard register and hide the address-reload loss.
!
! Exact commands from worktree root, in bootstrap Cygwin bash:
! base=/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap
! export PATH="$base/cross/bin:/usr/bin:/bin"
! mkdir -p tests/out
! k1om-mpss-linux-gfortran -w -ffree-form -ffree-line-length-none \
!   -fconvert=big-endian -frecord-marker=4 -std=legacy -O1 -mknc \
!   -fno-tree-vectorize -Jtests/out -S -fdump-rtl-reload \
!   tests/regress/knc-secondary-reload.f90 -o tests/out/donor.s
! mv tests/out/knc-secondary-reload.f90.*reload tests/out/donor.reload
! k1om-mpss-linux-gfortran -B"$base/reference/gcc-lra-diagnostic/" \
!   -w -ffree-form -ffree-line-length-none -fconvert=big-endian \
!   -frecord-marker=4 -std=legacy -O1 -mknc -fno-tree-vectorize \
!   -Jtests/out -S -fdump-rtl-reload tests/regress/knc-secondary-reload.f90 \
!   -o tests/out/reference.s
! mv tests/out/knc-secondary-reload.f90.*reload tests/out/reference.reload
!
! Results: both compilers exit 0; the donor FAILS the preserved RTL symptom,
! the diagnostic reference PASSES it. This is not a native execution result.
! Donor: before Deleting move 2063, Creating newreg=2608 from oldreg=758
! to address r2608; replacement 4947 stores through r2608*4+r1914, but
! r2608:DI=r758:DI is absent throughout the dump. Its address setup was lost.
! Reference: replacement 4946 stores through the original r758*4+r1914;
! no missing address setup. Both delete the move, so deletion alone is no test.
! All stores checked by pairing each Deleting move with address creation in its
! preceding 14 lines, then searching the dump for rNEW:mode=rOLD:mode:
! donor missing pairs: 1291 (2470<-309, 2471<-523), 2063 (2608<-758),
! 2765 (2727<-1825); reference: none. No assembler, linker or card run.
module module_channel_routing
use iso_fortran_env, only: int64
implicit none
integer :: my_id, io_id, left_id, right_id, up_id, down_id
interface
  subroutine updateLinkV(inV,outV)
    real(kind=8), dimension(:) :: inV
    real, dimension(:) :: outV
  end subroutine
  subroutine gbcastReal2(index,size1,inV,insize,outV)
    integer :: size1,insize
    integer, dimension(:) :: index
    real, dimension(:) :: inV,outV
  end subroutine
  subroutine updateLake_seq(a,n,b)
    integer :: n
    real, dimension(:), intent(inout), asynchronous :: a
    real, dimension(:), intent(in) :: b
  end subroutine
end interface
contains
     Subroutine drive_CHANNEL(did, latval,lonval,KT, IXRT,JXRT, SUBRTSWCRT, &
       QSUBRT, LAKEINFLORT, QSTRMVOLRT, TO_NODE, FROM_NODE, &
       TYPEL, ORDER, MAXORDER, NLINKS, CH_NETLNK, CH_NETRT, CH_LNKRT, &
       LAKE_MSKRT, DT, DTCT, DTRT_CH,MUSK, MUSX, QLINK, &
       QLateral, &
       HLINK, ELRT, CHANLEN, MannN, So, ChSSlp, Bw, Tw, Tw_CC, n_CC,  &
       ChannK, RESHT, HRZAREA, LAKEMAXH, WEIRH, WEIRC, WEIRL, ORIFICEC, ORIFICEA, ORIFICEE, &
       ZELEV, CVOL, NLAKES, QLAKEI, QLAKEO, LAKENODE, &
       dist, QINFLOWBASE, CHANXI, CHANYJ, channel_option, RETDEP_CHAN, &
       NLINKSL, LINKID, node_area, lake_lookup  &
       , lake_index,link_location,mpp_nlinks,nlinks_index,yw_mpp_nlinks  &
       , LNLINKSL, LLINKID  &
       , gtoNode,toNodeInd,nToNodeInd &
       , CH_LNKRT_SL &
       ,gwBaseSwCRT, gwHead, qgw_chanrt, gwChanCondSw, gwChanCondConstIn, &
       gwChanCondConstOut, velocity, qloss)
       IMPLICIT NONE
 real, external :: DIFFUSION, HEAD, CRITICALDEPTH, MUSKING
        INTEGER, INTENT(IN) :: did, IXRT,JXRT,channel_option
        INTEGER, INTENT(IN) :: NLINKS,NLAKES, NLINKSL
        integer, INTENT(INOUT) :: KT   ! flag of cold start (1) or continue run.
        REAL, INTENT(IN), DIMENSION(IXRT,JXRT)    :: QSUBRT
        REAL, INTENT(IN), DIMENSION(IXRT,JXRT)    :: QSTRMVOLRT
        REAL, INTENT(IN), DIMENSION(IXRT,JXRT)    :: LAKEINFLORT
        REAL, INTENT(IN), DIMENSION(IXRT,JXRT)    :: ELRT
        REAL, INTENT(IN), DIMENSION(IXRT,JXRT)    :: QINFLOWBASE
        INTEGER(kind=int64), INTENT(IN), DIMENSION(IXRT,JXRT) :: CH_NETLNK
        INTEGER, INTENT(IN), DIMENSION(IXRT,JXRT) :: CH_NETRT
        INTEGER(kind=int64), INTENT(IN), DIMENSION(IXRT,JXRT) :: CH_LNKRT
        INTEGER(kind=int64), INTENT(IN), DIMENSION(IXRT,JXRT) :: CH_LNKRT_SL
       real , dimension(ixrt,jxrt):: latval,lonval
        INTEGER, INTENT(IN), DIMENSION(IXRT,JXRT) :: LAKE_MSKRT
        INTEGER, INTENT(IN), DIMENSION(NLINKS)    :: ORDER, TYPEL !--link
        INTEGER(kind=int64), INTENT(IN), DIMENSION(NLINKS)    :: TO_NODE, FROM_NODE
        INTEGER, INTENT(IN), DIMENSION(NLINKS)    :: CHANXI, CHANYJ
        REAL,    INTENT(IN), DIMENSION(NLINKS)    :: ZELEV  !--elevation of nodes
        REAL, INTENT(INOUT), DIMENSION(NLINKS)    :: CVOL
        REAL, INTENT(IN), DIMENSION(NLINKS)       :: MUSK, MUSX
        REAL, INTENT(IN), DIMENSION(NLINKS)       :: CHANLEN
        REAL, INTENT(IN), DIMENSION(NLINKS)       :: So, MannN
        REAL, INTENT(IN), DIMENSION(NLINKS)       :: ChSSlp,Bw,Tw  !--properties of nodes or links
        REAL, INTENT(IN), DIMENSION(NLINKS)       :: Tw_CC, n_CC  !properties of compund channel
        REAL, INTENT(IN), DIMENSION(NLINKS)       :: ChannK  !--Channel Infiltration
        REAL                                      :: Km, X
        REAL , INTENT(INOUT), DIMENSION(:,:) :: QLINK
        REAL ,  DIMENSION(NLINKS,2) :: tmpQLINK
        REAL , INTENT(INOUT), DIMENSION(NLINKS)   :: HLINK
        REAL, dimension(NLINKS), intent(inout)    :: QLateral !--lateral flow
        REAL, INTENT(IN)                          :: DT    !-- model timestep
        REAL, INTENT(IN)                          :: DTRT_CH  !-- routing timestep
        REAL, INTENT(INOUT)                       :: DTCT
        real                                      :: minDTCT !BF minimum routing timestep
        REAL                                      :: dist(ixrt,jxrt,9)
        REAL                                      :: RETDEP_CHAN
        INTEGER, INTENT(IN)                       :: MAXORDER, SUBRTSWCRT, &
                                                     gwBaseSwCRT, gwChanCondSw
        real, intent(in)                          :: gwChanCondConstIn, gwChanCondConstOut ! aquifer-channel conductivity constant from namelist
        REAL , INTENT(IN), DIMENSION(NLINKS)      :: node_area
        real, dimension(:), INTENT(inout)         :: velocity, qloss
        REAL, DIMENSION(NLINKS)                   :: dzGwChanHead
        REAL, DIMENSION(NLINKS)                   :: Q_GW_CHAN_FLUX     !DJG !!! Change 'INTENT' to 'OUT' when ready to update groundwater state...
        REAL, DIMENSION(IXRT,JXRT)                :: ZWATTBLRT          !DJG !!! Match with subsfce/gw routing & Change 'INTENT' to 'INOUT' when ready to update groundwater state...
        REAL, INTENT(INOUT), DIMENSION(:,:), allocatable :: gwHead      !DJG !!! groundwater head from Fersch-2d gw implementation...units (m ASL)
        REAL, INTENT(INOUT), DIMENSION(:,:), allocatable :: qgw_chanrt  !DJG !!! Channel-gw flux as used in Fersch 2d gw implementation...units (m^3/s)...Change 'INTENT' to 'OUT' when ready to update groundwater state...
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: HRZAREA  !-- horizontal area (km^2)
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: LAKEMAXH !-- maximum lake depth  (m^2)
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: WEIRH    !-- lake depth  (m^2)
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: WEIRC    !-- weir coefficient
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: WEIRL    !-- weir length (m)
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: ORIFICEC !-- orrifice coefficient
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: ORIFICEA !-- orrifice area (m^2)
        REAL, INTENT(IN), DIMENSION(NLAKES)       :: ORIFICEE !-- orrifce elevation (m)
        REAL, INTENT(INOUT), DIMENSION(NLAKES)    :: RESHT    !-- reservoir height (m)
        REAL*8,  DIMENSION(NLAKES)    :: QLAKEI8   !-- lake inflow (cms)
        REAL, INTENT(INOUT), DIMENSION(NLAKES)    :: QLAKEI   !-- lake inflow (cms)
        REAL,                DIMENSION(NLAKES)    :: QLAKEIP  !-- lake inflow previous timestep (cms)
        REAL, INTENT(INOUT), DIMENSION(NLAKES)    :: QLAKEO   !-- outflow from lake used in diffusion scheme
        INTEGER(kind=int64), INTENT(IN), DIMENSION(NLINKS)    :: LAKENODE !-- outflow from lake used in diffusion scheme
        INTEGER(kind=int64), INTENT(IN), DIMENSION(NLINKS)    :: LINKID   !--  id of channel elements for linked scheme
        REAL, DIMENSION(NLINKS)                   :: QSUM     !--mass bal of node
        REAL*8, DIMENSION(NLINKS)                   :: QSUM8     !--mass bal of node
        REAL, DIMENSION(NLAKES)                   :: QLLAKE   !-- lateral inflow to lake in diffusion scheme
        REAL*8, DIMENSION(NLAKES)                   :: QLLAKE8   !-- lateral inflow to lake in diffusion scheme
        integer, intent(in), dimension(:)     :: lake_lookup  !-- inverse lake index for k->lake mapping
        INTEGER                     :: i,j,k,t,m,jj,kk,KRT,node,l_idx, lakeid
        INTEGER                     :: DT_STEPS               !-- number of timestep in routing
        REAL                        :: Qup,Quc                !--Q upstream Previous, Q Upstream Current, downstream Previous
        REAL                        :: bo                     !--critical depth, bnd outflow just for testing
        REAL                        :: AREA,WP                !--wetted area and perimiter for MuskingC. routing
        REAL ,DIMENSION(NLINKS)     :: HLINKTMP,CVOLTMP       !-- temporarily store head values and volume values
        REAL ,DIMENSION(NLINKS)     :: CD                     !-- critical depth
        real, DIMENSION(IXRT,JXRT)  :: tmp
        real, dimension(nlinks)     :: tmp2
        integer lake_index(nlakes)
        integer nlinks_index(nlinks)
        integer mpp_nlinks, iyw, yw_mpp_nlinks
        integer(kind=int64) link_location(ixrt,jxrt)
        real     ywtmp(ixrt,jxrt)
        integer LNLINKSL
        integer(kind=int64), dimension(LNLINKSL) :: LLINKID
        real(kind=8),  dimension(LNLINKSL) :: LQLateral
        integer, dimension(:) ::  toNodeInd
        integer(kind=int64), dimension(:,:) ::  gtoNode
        integer  :: nToNodeInd
        real, dimension(nToNodeInd,2) :: gQLINK
        real, allocatable,dimension(:) :: tmpQLAKEO, tmpQLAKEI, tmpRESHT
        integer flag
        integer :: n, kk2, nt, nsteps  ! tmp
       if(my_id == io_id) then
           allocate(tmpQLAKEO(NLAKES))
           allocate(tmpQLAKEI(NLAKES))
           allocate(tmpRESHT(NLAKES))
        endif
        QLAKEIP = 0
        QLAKEI8 = 0
        HLINKTMP = 0
        CVOLTMP = 0
        CD = 0
        node = 1
        QLateral = 0
        QSUM     = 0
        QLLAKE   = 0
      dzGwChanHead = 0.
   IF(channel_option .ne. 3) then   !--muskingum methods ROUTE ON DT timestep, not DTRT!!
         nsteps = (DT+0.5)/DTRT_CH
         LQLateral = 0          !-- initial lateral flow to 0 for this reach
         DO iyw = 1,yw_MPP_NLINKS
         jj = nlinks_index(iyw)
              if( .not. (  (CHANXI(jj) .eq. 1 .and. left_id .ge. 0) .or. &
                           (CHANXI(jj) .eq. ixrt .and. right_id .ge. 0) .or. &
                           (CHANYJ(jj) .eq. 1 .and. down_id .ge. 0) .or. &
                           (CHANYJ(jj) .eq. jxrt .and. up_id .ge. 0)      &
                   ) ) then
                  if (CH_LNKRT_SL(CHANXI(jj),CHANYJ(jj)) .gt. 0) then
                     k = CH_LNKRT_SL(CHANXI(jj),CHANYJ(jj))
                     LQLateral(k) = LQLateral(k)+((QSTRMVOLRT(CHANXI(jj),CHANYJ(jj))+QINFLOWBASE(CHANXI(jj),CHANYJ(jj)))/1000 &
                            *node_area(jj)/DT)
                  elseif ( (LAKE_MSKRT(CHANXI(jj),CHANYJ(jj)) .gt. 0)) then !-lake grid
                      k = LAKE_MSKRT(CHANXI(jj),CHANYJ(jj))
                      LQLateral(k) = LQLateral(k) +((LAKEINFLORT(CHANXI(jj),CHANYJ(jj))+QINFLOWBASE(CHANXI(jj),CHANYJ(jj)))/1000 &
                               *node_area(jj)/DT)
                  endif
              endif
         end do  ! jj
       call updateLinkV(LQLateral, QLateral(1:NLINKSL))
   do nt = 1, nsteps
       gQLINK = 0.000
       call gbcastReal2(toNodeInd,nToNodeInd,QLINK(1:NLINKSL,2), NLINKSL, gQLINK(:,2))
       call gbcastReal2(toNodeInd,nToNodeInd,QLINK(1:NLINKSL,1), NLINKSL, gQLINK(:,1))
       tmpQlink = 0.0
       if(my_id .eq. io_id) then
            tmpQLAKEO = QLAKEO
            tmpQLAKEI = QLAKEI
            tmpRESHT = RESHT
       endif
       do k = 1,NLINKSL
             Quc  = 0.0
             Qup  = 0.0
               do n = 1, gtoNODE(k,1)
                  m = gtoNODE(k,n+1)
                    Quc = Quc + gQLINK(m,2)  !--accum of upstream inflow of current timestep (2)
                    Qup = Qup + gQLINK(m,1)  !--accum of upstream inflow of previous timestep (1)
                end do ! do i
                if(TYPEL(k) == 1) then   !--link is a reservoir
                    l_idx = lake_lookup(k)
                    if (l_idx >= 0) then     !-- -999 if not a reservoir in the lookup table (belt-and-suspenders check)
                        QLAKEO(l_idx)  = QLINK(k,2)     !save outflow to lake
                        QLAKEI(l_idx)  = Quc            !save inflow to lake
                    end if
                elseif (channel_option .eq. 1) then  !muskingum routing
                       Km = MUSK(k)
                       X = MUSX(k)
                       tmpQLINK(k,2) = MUSKING(k,Qup,(Quc+QLateral(k)),QLINK(k,1),DTRT_CH,Km,X) !upstream plus lateral inflow
                   elseif (channel_option .eq. 2) then ! muskingum cunge
                   call SUBMUSKINGCUNGE(tmpQLINK(k,2), velocity(k), qloss(k), LINKID(k),  &
                    Qup,Quc, QLINK(k,1), QLateral(k),   DTRT_CH, So(k), &
                    CHANLEN(k), MannN(k), ChSSlp(k), Bw(k), Tw(k),Tw_CC(k), n_CC(k),  HLINK(k), ChannK(k) )
                else
                    print *, "FATAL ERROR: no channel option selected"
                    call hydro_stop("In drive_CHANNEL() - no channel option selected")
                   endif
         end do       !--k links
         call updateLake_seq(RESHT,nlakes,tmpRESHT)
         call updateLake_seq(QLAKEO,nlakes,tmpQLAKEO)
         call updateLake_seq(QLAKEI,nlakes,tmpQLAKEI)
          do k = 1, NLINKSL
            if(TYPEL(k) .ne. 1) then
               QLINK(k,2) = tmpQLINK(k,2)
            endif
            QLINK(k,1) = QLINK(k,2)    !assing link flow of current to be previous for next time step
         end do
   end do ! nsteps
   elseif(channel_option .eq. 3) then   !--- route using the diffusion scheme on nodes not links
         call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,HLINK,NLINKS,99)
         call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,CVOL,NLINKS,99)
         KRT = 0                  !-- initialize the time counter
         minDTCT = 0.01           ! define minimum routing sub-timestep (s), simulation will end with smaller timestep
         DTCT = min(max(DTCT*2.0, minDTCT),DTRT_CH)
         HLINKTMP = HLINK         !-- temporary storage of the water elevations (m)
         CVOLTMP = CVOL           !-- temporary storage of the volume of water in channel (m^3)
         QLAKEIP = QLAKEI         !-- temporary lake inflow from previous timestep  (cms)
 crnt:   DO                      !-- loop on the courant condition
          QSUM     = 0.              !-- initialize the total flow out of each cell to zero
          QSUM8     = 0.              !-- initialize the total flow out of each cell to zero
          QLAKEI8  = 0.              !-- set the lake inflow as zero
          QLAKEI   = 0.              !-- set the lake inflow as zero
          QLLAKE   = 0.              !-- initialize each lake's lateral inflow to zero
          QLLAKE8   = 0.              !-- initialize each lake's lateral inflow to zero
          DT_STEPS = INT(DT/DTCT)   !-- fix the timestep
          QLateral = 0.
          if(gwBaseSwCRT == 3) then
	  Q_GW_CHAN_FLUX = 0.
	  qgw_chanrt     = 0.
          end if
         DO iyw = 1,yw_MPP_NLINKS
         i = nlinks_index(iyw)
           if(node_area(i) .eq. 0) then
               write(6,*) "FATAL ERROR: node_area(i) is zero. i=", i
               call hydro_stop("In drive_CHANNEL() - Error node_area")
           endif
nodeType:if((CH_NETRT(CHANXI(i), CHANYJ(i) ) .eq. 0) .and. &
              (LAKE_MSKRT(CHANXI(i),CHANYJ(i)) .lt.0) ) then !--a reg. node
gwOption:   if(gwBaseSwCRT == 3) then
             dzGwChanHead(i) = gwHead(CHANXI(i),CHANYJ(i)) - (HLINK(i)+ZELEV(i))
             if(gwChanCondSw .eq. 0) then
                qgw_chanrt(CHANXI(i),CHANYJ(i)) = 0.
             else if(gwChanCondSw .eq. 1 .and. dzGwChanHead(i) > 0) then
                qgw_chanrt(CHANXI(i),CHANYJ(i)) = gwChanCondConstIn * dzGwChanHead(i) &
                                                * CHANLEN(i) * 2.
             else if(gwChanCondSw .eq. 1 .and. dzGwChanHead(i) < 0) then
                qgw_chanrt(CHANXI(i),CHANYJ(i)) = max(-0.005, gwChanCondConstOut * dzGwChanHead(i) &
                                                * CHANLEN(i) * 2.)
             else
	        qgw_chanrt(CHANXI(i),CHANYJ(i)) = 0.
             end if
             Q_GW_CHAN_FLUX(i) = qgw_chanrt(CHANXI(i),CHANYJ(i))
            else
	      Q_GW_CHAN_FLUX(i) = 0.
	    end if gwOption
              QLateral(CH_NETLNK(CHANXI(i),CHANYJ(i))) =  &
                Q_GW_CHAN_FLUX(i)+&
                ((QSTRMVOLRT(CHANXI(i),CHANYJ(i))+&
                 QINFLOWBASE(CHANXI(i),CHANYJ(i))) &
                   /DT_STEPS*node_area(i)/1000/DTCT)
	       if((QLateral(CH_NETLNK(CHANXI(i),CHANYJ(i))).lt.0.) .and. (gwChanCondSw == 0)) then
               elseif (QLateral(CH_NETLNK(CHANXI(i),CHANYJ(i))) .gt. 1.0) then
               end if
         elseif(LAKE_MSKRT(CHANXI(i),CHANYJ(i)) .gt. 0 .and. &
                (CH_NETRT(CHANXI(i),CHANYJ(i)) .le. 0)) then !--a lake node
              QLLAKE8(LAKE_MSKRT(CHANXI(i),CHANYJ(i))) = &
                 QLLAKE8(LAKE_MSKRT(CHANXI(i),CHANYJ(i))) + &
                 (LAKEINFLORT(CHANXI(i),CHANYJ(i))+ &
                 QINFLOWBASE(CHANXI(i),CHANYJ(i))) &
                 /DT_STEPS*node_area(i)/1000/DTCT
         elseif(CH_NETRT(CHANXI(i),CHANYJ(i)) .gt. 0) then  !pour out of lake
                 QLateral(CH_NETLNK(CHANXI(i),CHANYJ(i))) =  &
                   QLAKEO(CH_NETRT(CHANXI(i),CHANYJ(i)))  !-- previous timestep
         endif nodeType
        ENDDO
    call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,QLateral,NLINKS,99)
    if(NLAKES .gt. 0) then
       call sum_real8(QLLAKE8,NLAKES)
       QLLAKE = QLLAKE8
    endif
         DO iyw = 1,yw_MPP_NLINKS
         i = nlinks_index(iyw)
           if (TYPEL(i) .eq. 0 .AND. HLINKTMP(FROM_NODE(i)) .gt. RETDEP_CHAN) then
               if(from_node(i) .ne. to_node(i) .and. (to_node(i) .gt. 0) .and.(from_node(i) .gt. 0) ) &  ! added by Wei Yu
                   QLINK(i,1)=DIFFUSION(i,ZELEV(FROM_NODE(i)),ZELEV(TO_NODE(i)), &
                     HLINKTMP(FROM_NODE(i)),HLINKTMP(TO_NODE(i)), &
                     CHANLEN(i), MannN(i), Bw(i), ChSSlp(i))
            else !--  we are just computing critical depth for outflow points
               QLINK(i,1) =0.
            endif
          ENDDO
    call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,QLINK(:,1),NLINKS,99)
         DO iyw = 1,yw_mpp_nlinks
         i = nlinks_index(iyw)
           if(TYPEL(i) .eq. 0) then                                       !-- only regular nodes have to attribute
              QSUM8(TO_NODE(i)) = QSUM8(TO_NODE(i)) + QLINK(i,1)
           endif
          END DO
    call MPP_CHANNEL_COM_REAL8(Link_location,ixrt,jxrt,qsum8,NLINKS,0)
    qsum = qsum8
         do iyw = 1,yw_mpp_nlinks
         i = nlinks_index(iyw)
            QSUM(FROM_NODE(i)) = QSUM(FROM_NODE(i)) - QLINK(i,1)
         end do
    call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,qsum,NLINKS,99)
         flag = 99
         do iyw = 1,yw_MPP_NLINKS
             i = nlinks_index(iyw)
           if( TYPEL(i).eq.0 .and. CVOLTMP(i) .ge. 0.001 .and.(CVOLTMP(i)-QSUM(i)*DTCT)/CVOLTMP(i) .le. -0.01 ) then
            flag = -99
            goto 999
            endif
          enddo
999 continue
        call mpp_same_int1(flag)
        if(flag < 0  .and. DTCT >0.1)   then
             if(DTCT .gt. minDTCT) then                !-- timestep in seconds
              DTCT = max(DTCT/2 , minDTCT)             !-- 1/2 timestep
              KRT = 0                                  !-- restart counter
              HLINKTMP = HLINK                         !-- set head and vol to start value of timestep
              CVOLTMP = CVOL
              CYCLE crnt                               !-- start cycle over with smaller timestep
             else
              write(6,*) "Courant error with smallest routing timestep DTCT: ",DTCT
              DTCT = 0.1
              HLINKTMP = HLINK                          !-- set head and volume to start values of timestep
              CVOLTMP  = CVOL
              goto 998
             end if
        endif
998 continue
        do iyw = 1,yw_MPP_NLINKS
            i = nlinks_index(iyw)
           if(TYPEL(i) .eq. 0) then                   !--  regular channel grid point, compute volume
              CVOLTMP(i) = CVOLTMP(i) + (QSUM(i) + QLateral(i) )* DTCT
              if((CVOLTMP(i) .lt. 0) .and. (gwChanCondSw == 0)) then
                CVOLTMP(i) =0
              endif
           elseif(TYPEL(i) .eq. 1) then               !-- pour point, critical depth downstream
              if (QSUM(i)+QLateral(i) .lt. 0) then
              else
                  CD(i) = HLINKTMP(i)  !This is a temp hardwire for flow depth for the pour point...
              endif
                   CVOLTMP(i) = CVOLTMP(i) + (QSUM(i) + QLateral(i) - &
                       DIFFUSION(i,ZELEV(i),ZELEV(i)-(So(i)*CHANLEN(i)),HLINKTMP(i), &
                       CD(i),CHANLEN(i), MannN(i), Bw(i), ChSSlp(i)) ) * DTCT
          elseif (TYPEL(i) .eq. 2) then              !--- into a reservoir, assume critical depth
              if ((QSUM(i)+QLateral(i) .lt. 0) .and. (gwChanCondSw == 0)) then
             else
               CD(i) = HLINKTMP(i)  !This is a temp hardwire for flow depth for the pour point...
             endif
                   CVOLTMP(i) = CVOLTMP(i) + (QSUM(i) + QLateral(i) - &
                          DIFFUSION(i,ZELEV(i),ZELEV(i)-(So(i)*CHANLEN(i)),HLINKTMP(i), &
                             CD(i) ,CHANLEN(i), MannN(i), Bw(i), ChSSlp(i)) ) * DTCT
          else
              print *, "FATAL ERROR: This node does not have a type.. error TYPEL =", TYPEL(i)
              call hydro_stop("In drive_CHANNEL() - error TYPEL")
          endif
          if(TYPEL(i) == 0) then !-- regular channel node, finalize head and flow
              HLINKTMP(i) = HEAD(i, CVOLTMP(i)/CHANLEN(i),Bw(i),1/ChSSlp(i))  !--updated depth
          else
              HLINKTMP(i) = CD(i)  !!!   CRITICALDEPTH(i,QSUM(i)+QLateral(i), Bw(i), 1./ChSSlp(i)) !--critical depth is head
          endif
          if(TO_NODE(i) .gt. 0) then
             if(LAKENODE(TO_NODE(i)) .gt. 0) then
                  QLAKEI8(LAKENODE(TO_NODE(i))) = QLAKEI8(LAKENODE(TO_NODE(i))) + QLINK(i,1)
             endif
          endif
        END DO  !--- done processing all the links
    call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,CVOLTMP,NLINKS,99)
    call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,CD,NLINKS,99)
    if(NLAKES .gt. 0) then
        call sum_real8(QLAKEI8,NLAKES)
        QLAKEI = QLAKEI8
    endif
    call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,HLINKTMP,NLINKS,99)
           do i = 1, NLAKES !-- mass balances of lakes
            if(lake_index(i) .gt. 0)  then
              QLAKEIP(i) = QLAKEI(i)  !-- store total lake inflow for this timestep
            endif
           enddo
    if(NLAKES .gt. 0) then
         call updateLake_grid(QLLAKE, nlakes,lake_index)
         call updateLake_grid(RESHT,  nlakes,lake_index)
         call updateLake_grid(QLAKEO, nlakes,lake_index)
         call updateLake_grid(QLAKEI, nlakes,lake_index)
         call updateLake_grid(QLAKEIP,nlakes,lake_index)
    endif
         do iyw = 1,yw_MPP_NLINKS
            i = nlinks_index(iyw)
            if(TYPEL(i) == 0) then !-- regular channel node, finalize head and flow
                   QLINK(i,1)=DIFFUSION(i,ZELEV(FROM_NODE(i)),ZELEV(TO_NODE(i)), &
                      HLINKTMP(FROM_NODE(i)),HLINKTMP(TO_NODE(i)), &
                      CHANLEN(i), MannN(i), Bw(i), ChSSlp(i))
            endif
         enddo
          call MPP_CHANNEL_COM_REAL(Link_location,ixrt,jxrt,QLINK(:,1),NLINKS,99)
           KRT = KRT + 1                     !-- iterate on the timestep
           if(KRT .eq. DT_STEPS) exit crnt   !-- up to the maximum time in interval
          end do crnt   !--- DTCT timestep of DT_STEPS
           HLINK = HLINKTMP                 !-- update head based on final solution in timestep
           CVOL  = CVOLTMP                  !-- update volume
        else                                !-- no channel option apparently selected
         print *, "FATAL ERROR: no channel option selected"
         call hydro_stop("In drive_CHANNEL() - no channel option selected")
        endif
        if (KT .eq. 1) KT = KT + 1
       if (my_id == io_id) then
           if(allocated(tmpRESHT))  deallocate(tmpRESHT)
           if(allocated(tmpQLAKEO))  deallocate(tmpQLAKEO)
           if(allocated(tmpQLAKEI))  deallocate(tmpQLAKEI)
       endif
end subroutine drive_CHANNEL
end module

