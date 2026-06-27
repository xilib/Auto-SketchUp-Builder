# building_tools.rb - v3.0 Full Architectural Detail Engine
# ============================================================
require 'sketchup.rb'


# ============================================================
# PARAMETRIC WINDOW ENGINE (Advanced Generative Algorithm)
# ============================================================

# ============================================================
# PARAMETRIC DOOR ENGINE (Advanced Generative Algorithm)
# ============================================================

# ============================================================
# PARAMETRIC DORMER ENGINE
# ============================================================
module ParametricDormer
  def self.generate(p1, vx, vy, vn, w, h, style, window_style, pitch_deg=35.0)
    model = Sketchup.active_model
    model.start_operation("Parametric Dormer", true)
    g = model.entities.add_group
    
    mats = model.materials
    mw = mats["WhitePaint"] || mats.add("WhitePaint")
    mw.color = "White"
    mr = mats["RoofMaterial"] || mats.add("RoofMaterial")
    mr.color = [50, 60, 70]
    
    pr = pitch_deg * Math::PI / 180.0
    d = h / Math.tan(pr)
    
    p2 = [p1[0]+vx[0]*w, p1[1]+vx[1]*w, p1[2]]
    p3 = [p2[0], p2[1], p2[2]+h]
    p4 = [p1[0], p1[1], p1[2]+h]
    
    # Fix: Back points go INTO the roof (-d instead of d)
    bp1 = [p1[0]+vn[0]*-d, p1[1]+vn[1]*-d, p1[2]+h]
    bp2 = [p2[0]+vn[0]*-d, p2[1]+vn[1]*-d, p2[2]+h]
    
    left_cheek = g.entities.add_face(p1, p4, bp1)
    left_cheek.material = mw if left_cheek
    
    right_cheek = g.entities.add_face(p2, bp2, p3)
    right_cheek.material = mw if right_cheek
    
    ww = w - 12.0
    wh = h - 12.0
    wp1 = [p1[0]+vx[0]*6.0, p1[1]+vx[1]*6.0, p1[2]+6.0]
    wp2 = [wp1[0]+vx[0]*ww, wp1[1]+vx[1]*ww, wp1[2]]
    wp3 = [wp2[0], wp2[1], wp2[2]+wh]
    wp4 = [wp1[0], wp1[1], wp1[2]+wh]
    
    ff = g.entities.add_face(p1, p2, p3, p4)
    if ff
      hole = g.entities.add_face(wp1, wp2, wp3, wp4)
      hole.erase! if hole
      ff.material = mw
    end
    
    oh = 8.0 
    if style == "shed"
      rg = g.entities.add_group
      rg.name = "DormerRoof"
      rf = rg.entities.add_face(
        [p4[0]-vx[0]*oh+vn[0]*oh, p4[1]-vx[1]*oh+vn[1]*oh, p4[2]+3.0],
        [p3[0]+vx[0]*oh+vn[0]*oh, p3[1]+vx[1]*oh+vn[1]*oh, p3[2]+3.0],
        [bp2[0]+vx[0]*oh, bp2[1]+vx[1]*oh, bp2[2]+3.0],
        [bp1[0]-vx[0]*oh, bp1[1]-vx[1]*oh, bp1[2]+3.0]
      )
      if rf
        rf.reverse! if rf.normal.z < 0
        rf.pushpull(4.0) rescue nil
      end
    else
      rh = (w/2.0) * Math.tan(pr)
      apex_f = [p1[0]+vx[0]*(w/2.0), p1[1]+vx[1]*(w/2.0), p4[2]+rh]
      apex_b = [bp1[0]+vx[0]*(w/2.0), bp1[1]+vx[1]*(w/2.0), bp1[2]+rh]
      
      fg = g.entities.add_face(p4, p3, apex_f)
      fg.material = mw if fg
      
      rg = g.entities.add_group
      rg.name = "DormerRoof"
      rl = rg.entities.add_face(
        [p4[0]-vx[0]*oh+vn[0]*oh, p4[1]-vx[1]*oh+vn[1]*oh, p4[2]],
        [bp1[0]-vx[0]*oh, bp1[1]-vx[1]*oh, bp1[2]],
        [apex_b[0]+vn[0]*oh, apex_b[1]+vn[1]*oh, apex_b[2]+oh],
        [apex_f[0]+vn[0]*oh, apex_f[1]+vn[1]*oh, apex_f[2]+oh]
      )
      rl.pushpull(4.0) rescue nil if rl
      
      rr = rg.entities.add_face(
        [p3[0]+vx[0]*oh+vn[0]*oh, p3[1]+vx[1]*oh+vn[1]*oh, p3[2]],
        [apex_f[0]+vn[0]*oh, apex_f[1]+vn[1]*oh, apex_f[2]+oh],
        [apex_b[0]+vn[0]*oh, apex_b[1]+vn[1]*oh, apex_b[2]+oh],
        [bp2[0]+vx[0]*oh, bp2[1]+vx[1]*oh, bp2[2]]
      )
      rr.pushpull(4.0) rescue nil if rr
    end
    
    win_g = ParametricWindow.generate(wp1, vx, vy, vn, ww, wh, 2, 2, window_style, true, false, 2.0, 1.0, 2.0)
    if win_g
      g.entities.add_instance(win_g.definition, Geom::Transformation.new)
      win_g.erase! 
    end
    
    model.commit_operation
    g
  end
end

# ============================================================
# PARAMETRIC CANOPY ENGINE
# ============================================================
module ParametricCanopy
  def self.generate(p1, vx, vy, vn, w, d, style, support_style)
    model = Sketchup.active_model
    model.start_operation("Parametric Canopy", true)
    g = model.entities.add_group
    
    mats = model.materials
    mw = mats["WhitePaint"] || mats.add("WhitePaint")
    mw.color = "White"
    mr = mats["RoofMaterial"] || mats.add("RoofMaterial")
    mr.color = [50, 60, 70]
    
    p2 = [p1[0]+vx[0]*w, p1[1]+vx[1]*w, p1[2]]
    # Project outwards by depth d (vn points out)
    op1 = [p1[0]+vn[0]*d, p1[1]+vn[1]*d, p1[2]]
    op2 = [p2[0]+vn[0]*d, p2[1]+vn[1]*d, p2[2]]
    
    tv = 6.0
    
    if style == "gable"
      pitch = 30.0 * Math::PI / 180.0
      rh = (w/2.0) * Math.tan(pitch)
      apex_b = [p1[0]+vx[0]*(w/2.0), p1[1]+vx[1]*(w/2.0), p1[2]+rh]
      apex_f = [op1[0]+vx[0]*(w/2.0), op1[1]+vx[1]*(w/2.0), op1[2]+rh]
      
      # Gable front triangle
      fg = g.entities.add_face(op1, op2, apex_f)
      fg.material = mw if fg
      
      # Roof left and right in a subgroup so pushpulled faces inherit the material!
      rg = g.entities.add_group
      rg.name = "CanopyRoof"
      rl = rg.entities.add_face(op1, apex_f, apex_b, p1)
      rl.pushpull(4.0) rescue nil if rl
      rr = rg.entities.add_face(op2, p2, apex_b, apex_f)
      rr.pushpull(4.0) rescue nil if rr
    else
      # Flat/Shed in a subgroup
      rg = g.entities.add_group
      rg.name = "CanopyRoof"
      f = rg.entities.add_face(p1, p2, op2, op1)
      if f
        f.reverse! if f.normal.z < 0
        f.pushpull(tv) rescue nil
      end
    end
    
    # Supports
    if support_style == "brackets"
      bw = 4.0
      # Left bracket
      g.entities.add_face([p1[0], p1[1], p1[2]], [op1[0], op1[1], op1[2]], [p1[0], p1[1], p1[2]-d]).pushpull(bw) rescue nil
      # Right bracket
      g.entities.add_face([p2[0]-vx[0]*bw, p2[1]-vx[1]*bw, p2[2]], [op2[0]-vx[0]*bw, op2[1]-vx[1]*bw, op2[2]], [p2[0]-vx[0]*bw, p2[1]-vx[1]*bw, p2[2]-d]).pushpull(bw) rescue nil
    elsif support_style == "posts"
      pw = 6.0
      # Assumes posts go down to z=0
      g.entities.add_face([op1[0], op1[1], op1[2]], [op1[0]+vx[0]*pw, op1[1]+vx[1]*pw, op1[2]],
                          [op1[0]+vx[0]*pw, op1[1]+vx[1]*pw, 0], [op1[0], op1[1], 0]).pushpull(pw) rescue nil
      g.entities.add_face([op2[0]-vx[0]*pw, op2[1]-vx[1]*pw, op2[2]], [op2[0], op2[1], op2[2]],
                          [op2[0], op2[1], 0], [op2[0]-vx[0]*pw, op2[1]-vx[1]*pw, 0]).pushpull(pw) rescue nil
    end
    
    model.commit_operation
    g
  end
end

module ParametricDoor
  def self.generate(p1, vx, vy, vn, w, h, style, panes_x, panes_y, arch_top, has_transom, fd, lr)
    model = Sketchup.active_model
    model.start_operation("Parametric Door", true)
    g = model.entities.add_group
    
    mats = model.materials
    mg = mats["GlassColor"] || mats.add("GlassColor")
    mg.color = [140, 195, 225]
    mg.alpha = 0.6
    mw = mats["WhitePaint"] || mats.add("WhitePaint")
    mw.color = "White"
    md = mats["DoorPaint"] || mats.add("DoorPaint")
    md.color = [120, 80, 50] # nice wood/dark color by default
    
    p2=[p1[0]+vx[0]*w,p1[1]+vx[1]*w,p1[2]]
    p3=[p2[0]+vy[0]*h,p2[1]+vy[1]*h,p2[2]+vy[2]*h]
    p4=[p1[0]+vy[0]*h,p1[1]+vy[1]*h,p1[2]+vy[2]*h]
    
    transom_h = has_transom ? 16.0 : 0.0
    door_h = h - transom_h
    
    is_arch = arch_top
    arch_h = is_arch ? w/2.0 : 0.0
    
    # 1. Base Casing Frame
    cw = 4.0; cd = fd
    cf_pts = [
      [p1[0]-vx[0]*cw, p1[1]-vx[1]*cw, p1[2]],
      [p2[0]+vx[0]*cw, p2[1]+vx[1]*cw, p2[2]],
      [p3[0]+vx[0]*cw, p3[1]+vx[1]*cw, p3[2]+cw],
      [p4[0]-vx[0]*cw, p4[1]-vx[1]*cw, p4[2]+cw]
    ]
    cf = g.entities.add_face(cf_pts)
    if cf
      hole_pts = [p1, p2, p3, p4]
      hole = g.entities.add_face(hole_pts)
      hole.erase! if hole
      
      # The original cf reference is deleted by SketchUp when the hole is cut/erased!
      # We must find the newly created casing face, which is now the ONLY face in the group.
      cf = g.entities.grep(Sketchup::Face).first
      if cf
        dot_c = cf.normal.x * vn[0] + cf.normal.y * vn[1] + cf.normal.z * vn[2]
        cf.reverse! if dot_c < 0
        cf.pushpull(cd) rescue nil
        cf.material = mw rescue nil
      end
    end

    # Calculate frame recess Z offset
    front_z_offset = vn[0]*0.1 + vn[1]*0.1 + vn[2]*0.1 
    door_depth = lr
    
    # Transom logic
    if has_transom
      tp1 = [p4[0], p4[1], p4[2]-transom_h]
      tp2 = [p3[0], p3[1], p3[2]-transom_h]
      # Draw middle bar separating door and transom
      bar_pts = [
        [tp1[0], tp1[1], tp1[2]], [tp2[0], tp2[1], tp2[2]],
        [p3[0], p3[1], tp2[2]+4.0], [p4[0], p4[1], tp1[2]+4.0]
      ]
      bar = g.entities.add_face(bar_pts)
      if bar
         bar.pushpull(-door_depth) rescue nil
         bar.material = mw rescue nil
      end
      
      # Transom glass
      tg1 = [tp1[0]+vn[0]*-0.5, tp1[1]+vn[1]*-0.5, tp1[2]+4.0]
      tg2 = [tp2[0]+vn[0]*-0.5, tp2[1]+vn[1]*-0.5, tp2[2]+4.0]
      t_glass = g.entities.add_face(tg1, tg2, [tg2[0], tg2[1], p3[2]], [tg1[0], tg1[1], p4[2]])
      t_glass.material = mg if t_glass
    end
    
    # Door leaves
    door_h_actual = has_transom ? p4[2]-transom_h : p4[2]
    leaves = (style == "french" && w > 48) ? 2 : 1
    lw = w / leaves.to_f
    
    (0...leaves).each do |li|
      lp1 = [p1[0]+vx[0]*(li*lw), p1[1]+vx[1]*(li*lw), p1[2]]
      lp2 = [lp1[0]+vx[0]*lw, lp1[1]+vx[1]*lw, lp1[2]]
      lp3 = [lp2[0], lp2[1], door_h_actual]
      lp4 = [lp1[0], lp1[1], door_h_actual]
      
      # Recess door slightly inside casing
      l_rpts = [lp1, lp2, lp3, lp4].map{|pt| [pt[0]+vn[0]*1, pt[1]+vn[1]*1, pt[2]]}
      door_face = g.entities.add_face(l_rpts)
      next unless door_face
      
      dot_d = door_face.normal.x * vn[0] + door_face.normal.y * vn[1] + door_face.normal.z * vn[2]
      door_face.reverse! if dot_d < 0
      door_face.pushpull(-door_depth) rescue nil
      
      # Determine outer face of the door after pushpull
      out_f = [l_rpts[0], l_rpts[1], l_rpts[2], l_rpts[3]]
      
      if style == "french" || panes_x > 1 || panes_y > 1
        fm = 6.0
        gp1 = [out_f[0][0]+vx[0]*fm, out_f[0][1]+vx[1]*fm, out_f[0][2]+vy[2]*fm]
        gp2 = [out_f[1][0]-vx[0]*fm, out_f[1][1]-vx[1]*fm, out_f[1][2]+vy[2]*fm]
        gp3 = [gp2[0], gp2[1], out_f[2][2]-vy[2]*fm]
        gp4 = [gp1[0], gp1[1], out_f[3][2]-vy[2]*fm]
        g_pts = [gp1, gp2, gp3, gp4].map{|pt| [pt[0]+vn[0]*0.2, pt[1]+vn[1]*0.2, pt[2]]}
        glass = g.entities.add_face(g_pts)
        glass.material = mg if glass
        
        # Mullions inside the french door
        gw = (lw - 2*fm) / panes_x.to_f
        gh = (door_h_actual - 2*fm) / panes_y.to_f
        (1...panes_x).each do |i|
          mx = gp1[0] + vx[0]*(i*gw)
          my = gp1[1] + vx[1]*(i*gw)
          g.entities.add_face([mx-vx[0]*1+vn[0]*0.2, my-vx[1]*1+vn[1]*0.2, gp1[2]], [mx+vx[0]*1+vn[0]*0.2, my+vx[1]*1+vn[1]*0.2, gp1[2]],
                              [mx+vx[0]*1+vn[0]*0.2, my+vx[1]*1+vn[1]*0.2, gp4[2]], [mx-vx[0]*1+vn[0]*0.2, my-vx[1]*1+vn[1]*0.2, gp4[2]]).pushpull(0.5) rescue nil
        end
        (1...panes_y).each do |i|
          mz = gp1[2] + vy[2]*(i*gh)
          g.entities.add_face([gp1[0]+vn[0]*0.2, gp1[1]+vn[1]*0.2, mz-1], [gp2[0]+vn[0]*0.2, gp2[1]+vn[1]*0.2, mz-1],
                              [gp2[0]+vn[0]*0.2, gp2[1]+vn[1]*0.2, mz+1], [gp1[0]+vn[0]*0.2, gp1[1]+vn[1]*0.2, mz+1]).pushpull(0.5) rescue nil
        end
        
      elsif style == "sliding"
        # Sliding Door: two big glass panels
        fm = 4.0 # frame thickness
        gp1 = [out_f[0][0]+vx[0]*fm, out_f[0][1]+vx[1]*fm, out_f[0][2]+vy[2]*fm]
        gp2 = [out_f[1][0]-vx[0]*fm, out_f[1][1]-vx[1]*fm, out_f[1][2]+vy[2]*fm]
        gp3 = [gp2[0], gp2[1], out_f[2][2]-vy[2]*fm]
        gp4 = [gp1[0], gp1[1], out_f[3][2]-vy[2]*fm]
        # Offset second panel by -1 inch
        z_off = (li == 1) ? 1.0 : 0.0
        g_pts = [gp1, gp2, gp3, gp4].map{|pt| [pt[0]+vn[0]*(0.2-z_off), pt[1]+vn[1]*(0.2-z_off), pt[2]]}
        glass = g.entities.add_face(g_pts)
        glass.material = mg if glass
        
      elsif style == "garage_roller" || style == "garage"
        # Roller garage door
        sg_h = 8.0 # 8 inch horizontal slats
        num_slats = (door_h_actual / sg_h).to_i
        (1..num_slats).each do |si|
          bz = out_f[0][2] + si * sg_h
          # Horizontal groove
          gf = g.entities.add_face([out_f[0][0], out_f[0][1], bz-0.5], [out_f[1][0], out_f[1][1], bz-0.5],
                              [out_f[1][0], out_f[1][1], bz+0.5], [out_f[0][0], out_f[0][1], bz+0.5])
          if gf
            gf.reverse! if (gf.normal.x * vn[0] + gf.normal.y * vn[1] + gf.normal.z * vn[2]) < 0
            gf.pushpull(0.5) rescue nil
          end
        end
        
      elsif style == "garage_panel"
        # Sectioned 4x4 panel garage door
        sg_h = door_h_actual / 4.0
        (0..3).each do |si|
          bz = out_f[0][2] + si * sg_h
          tz = bz + sg_h
          # Horizontal groove
          gf = g.entities.add_face([out_f[0][0], out_f[0][1], tz-1], [out_f[1][0], out_f[1][1], tz-1],
                              [out_f[1][0], out_f[1][1], tz], [out_f[0][0], out_f[0][1], tz])
          if gf
            gf.reverse! if (gf.normal.x * vn[0] + gf.normal.y * vn[1] + gf.normal.z * vn[2]) < 0
            gf.pushpull(0.5) rescue nil
          end
          # Embossed panels
          pm = 6.0
          pf = g.entities.add_face([out_f[0][0]+vx[0]*pm, out_f[0][1]+vx[1]*pm, bz+pm],
                              [out_f[1][0]-vx[0]*pm, out_f[1][1]-vx[1]*pm, bz+pm],
                              [out_f[1][0]-vx[0]*pm, out_f[1][1]-vx[1]*pm, tz-pm],
                              [out_f[0][0]+vx[0]*pm, out_f[0][1]+vx[1]*pm, tz-pm])
          if pf
            pf.reverse! if (pf.normal.x * vn[0] + pf.normal.y * vn[1] + pf.normal.z * vn[2]) < 0
            pf.pushpull(1.0) rescue nil
          end
        end
        
      else
        # Solid door with raised panels
        pm = 6.0; pi_w = lw - pm*2
        ph1 = door_h_actual * 0.35
        ph2 = door_h_actual * 0.45
        gap = door_h_actual - ph1 - ph2 - pm*2
        
        # Bottom Panel
        pp1 = [out_f[0][0]+vx[0]*pm, out_f[0][1]+vx[1]*pm, out_f[0][2]+vy[2]*pm]
        pp2 = [pp1[0]+vx[0]*pi_w, pp1[1]+vx[1]*pi_w, pp1[2]]
        pp3 = [pp2[0], pp2[1], pp2[2]+vy[2]*ph1]
        pp4 = [pp1[0], pp1[1], pp1[2]+vy[2]*ph1]
        p_face = g.entities.add_face(pp1,pp2,pp3,pp4)
        p_face.pushpull(1.5) rescue nil if p_face
        
        # Top Panel
        tp1 = [out_f[0][0]+vx[0]*pm, out_f[0][1]+vx[1]*pm, out_f[0][2]+vy[2]*(pm+ph1+gap)]
        tp2 = [tp1[0]+vx[0]*pi_w, tp1[1]+vx[1]*pi_w, tp1[2]]
        tp3 = [tp2[0], tp2[1], tp2[2]+vy[2]*ph2]
        tp4 = [tp1[0], tp1[1], tp1[2]+vy[2]*ph2]
        t_face = g.entities.add_face(tp1,tp2,tp3,tp4)
        t_face.pushpull(1.5) rescue nil if t_face
        
        # Door handle (spherical knob approximation)
        kz = 36.0; kx = (li==0 ? lw-4.0 : 4.0)
        kpt = [out_f[0][0]+vx[0]*kx, out_f[0][1]+vx[1]*kx, out_f[0][2]+vy[2]*kz]
        g.entities.add_face([kpt[0]-1.5,kpt[1]-1.5,kpt[2]],[kpt[0]+1.5,kpt[1]-1.5,kpt[2]],
                            [kpt[0]+1.5,kpt[1]+1.5,kpt[2]],[kpt[0]-1.5,kpt[1]+1.5,kpt[2]]).pushpull(4) rescue nil
      end
    end
    
    # Paint entire group with door paint EXCEPT for glass which holds its own material
    g.material = md
    model.commit_operation
    g
  end
end

# ============================================================
# PARAMETRIC COLUMN ENGINE
# ============================================================
module ParametricColumn
  def self.generate(cx, cy, cn, col_height, col_w, style)
    model = Sketchup.active_model
    model.start_operation("Parametric Column", true)
    g = model.entities.add_group
    mats = model.materials
    mw = mats["WhitePaint"] || mats.add("WhitePaint")
    mw.color = "White"
    
    if style == "square"
      bf = g.entities.add_face([cx-col_w/2, cy-col_w/2, 0], [cx+col_w/2, cy-col_w/2, 0], [cx+col_w/2, cy+col_w/2, 0], [cx-col_w/2, cy+col_w/2, 0])
      bf.pushpull(-col_height) rescue nil
    elsif style == "fluted"
      # Simple fluted column (approximate as round for now, real fluted needs boolean ops or complex geometry)
      circle = g.entities.add_circle([cx, cy, 0], [0,0,1], col_w/2.0, 12)
      face = g.entities.add_face(circle)
      face.pushpull(-col_height) rescue nil
      # Add simple base and capital
      cb = g.entities.add_face([cx-col_w*0.6, cy-col_w*0.6, 0], [cx+col_w*0.6, cy-col_w*0.6, 0], [cx+col_w*0.6, cy+col_w*0.6, 0], [cx-col_w*0.6, cy+col_w*0.6, 0])
      cb.pushpull(-col_w*0.4) rescue nil
      cc = g.entities.add_face([cx-col_w*0.6, cy-col_w*0.6, col_height-col_w*0.4], [cx+col_w*0.6, cy-col_w*0.6, col_height-col_w*0.4], [cx+col_w*0.6, cy+col_w*0.6, col_height-col_w*0.4], [cx-col_w*0.6, cy+col_w*0.6, col_height-col_w*0.4])
      cc.pushpull(-col_w*0.4) rescue nil
    elsif style == "craftsman"
      # Craftsman tapered square column (brick base, tapered wood top)
      base_h = col_height * 0.4
      bw = col_w * 1.5
      # Base block
      bf = g.entities.add_face([cx-bw/2, cy-bw/2, 0], [cx+bw/2, cy-bw/2, 0], [cx+bw/2, cy+bw/2, 0], [cx-bw/2, cy+bw/2, 0])
      bf.pushpull(base_h) rescue nil if bf
      # Base cap
      bcf = g.entities.add_face([cx-bw/2-2, cy-bw/2-2, base_h], [cx+bw/2+2, cy-bw/2-2, base_h], [cx+bw/2+2, cy+bw/2+2, base_h], [cx-bw/2-2, cy+bw/2+2, base_h])
      bcf.pushpull(2) rescue nil if bcf
      
      # Tapered upper shaft
      tw = col_w
      top_w = col_w * 0.7
      
      # To do a perfect taper in API we connect faces manually
      pts_bt = [[cx-tw/2, cy-tw/2, base_h+2], [cx+tw/2, cy-tw/2, base_h+2], [cx+tw/2, cy+tw/2, base_h+2], [cx-tw/2, cy+tw/2, base_h+2]]
      pts_tp = [[cx-top_w/2, cy-top_w/2, col_height], [cx+top_w/2, cy-top_w/2, col_height], [cx+top_w/2, cy+top_w/2, col_height], [cx-top_w/2, cy+top_w/2, col_height]]
      (0..3).each do |i|
        ni = (i+1)%4
        g.entities.add_face(pts_bt[i], pts_bt[ni], pts_tp[ni], pts_tp[i]) rescue nil
      end
      g.entities.add_face(pts_tp) rescue nil
      
    else
      # Round Doric column
      col_r = col_w / 2.0
      sides = 16
      
      # Torus Base
      b_r = col_r * 1.4
      b_pts = []
      (0..sides).each { |s| a=s*2*Math::PI/sides; b_pts << [cx+b_r*Math.cos(a), cy+b_r*Math.sin(a), 0] }
      bf = g.entities.add_face(b_pts) rescue nil
      bf.pushpull(3) rescue nil if bf
      
      t_r = col_r * 1.2
      t_pts = []
      (0..sides).each { |s| a=s*2*Math::PI/sides; t_pts << [cx+t_r*Math.cos(a), cy+t_r*Math.sin(a), 3] }
      tf = g.entities.add_face(t_pts) rescue nil
      tf.pushpull(2) rescue nil if tf
      
      # Tapered Shaft
      shaft_top_r = col_r * 0.85
      top_z = col_height - 6.0
      (0...sides).each do |s|
        a1=s*2*Math::PI/sides; a2=(s+1)*2*Math::PI/sides
        p1 = [cx+col_r*Math.cos(a1), cy+col_r*Math.sin(a1), 5.0]
        p2 = [cx+col_r*Math.cos(a2), cy+col_r*Math.sin(a2), 5.0]
        p3 = [cx+shaft_top_r*Math.cos(a2), cy+shaft_top_r*Math.sin(a2), top_z]
        p4 = [cx+shaft_top_r*Math.cos(a1), cy+shaft_top_r*Math.sin(a1), top_z]
        g.entities.add_face(p1, p2, p3, p4) rescue nil
      end
      
      # Echinus and Abacus (Capital)
      c_pts = []
      (0..sides).each { |s| a=s*2*Math::PI/sides; c_pts << [cx+t_r*Math.cos(a), cy+t_r*Math.sin(a), top_z] }
      cf = g.entities.add_face(c_pts) rescue nil
      cf.pushpull(3) rescue nil if cf
      
      ab_w = b_r * 2.2
      abf = g.entities.add_face([cx-ab_w/2, cy-ab_w/2, top_z+3], [cx+ab_w/2, cy-ab_w/2, top_z+3], [cx+ab_w/2, cy+ab_w/2, top_z+3], [cx-ab_w/2, cy+ab_w/2, top_z+3])
      abf.pushpull(3) rescue nil if abf
    end
    
    g.material = mw
    model.commit_operation
    g
  end
end

module ParametricWindow
  def self.generate(p1, vx, vy, vn, w, h, panes_x, panes_y, style, has_sill, has_louvers, ft, mt, sp)
    model = Sketchup.active_model
    model.start_operation("Parametric Window", true)
    g = model.entities.add_group
    
    mats = model.materials
    mg = mats["GlassColor"] || mats.add("GlassColor")
    mg.color = [140, 195, 225]
    mg.alpha = 0.6
    mw = mats["WhitePaint"] || mats.add("WhitePaint")
    mw.color = "White"
    
    # 1. Hole Cutting Reference Points
    p2=[p1[0]+vx[0]*w,p1[1]+vx[1]*w,p1[2]]
    p3=[p2[0]+vy[0]*h,p2[1]+vy[1]*h,p2[2]+vy[2]*h]
    p4=[p1[0]+vy[0]*h,p1[1]+vy[1]*h,p1[2]+vy[2]*h]
    
    is_arch = (style == "arch_top")
    arch_h = is_arch ? w/2.0 : 0
    panes_x = 1 if style == "picture" || style == "awning"
    panes_y = 1 if style == "picture"
    
    if style == "chinese_lattice"
      panes_x = [2, (w / 6.0).to_i].max
      panes_y = [2, (h / 6.0).to_i].max
      mt = 1.0
    end
    
    if style == "bay_window"
      # Create protruding trapezoid
      bw_depth = 24.0
      bw_w = w * 0.5
      bw_side = w * 0.25
      p2=[p1[0]+vx[0]*w,p1[1]+vx[1]*w,p1[2]]
      p_bl = [p1[0]+vx[0]*bw_side+vn[0]*bw_depth, p1[1]+vx[1]*bw_side+vn[1]*bw_depth, p1[2]]
      p_br = [p2[0]-vx[0]*bw_side+vn[0]*bw_depth, p2[1]-vx[1]*bw_side+vn[1]*bw_depth, p2[2]]
      p_tl = [p_bl[0], p_bl[1], p1[2]+h]
      p_tr = [p_br[0], p_br[1], p2[2]+h]
      p3=[p2[0],p2[1],p2[2]+h]
      p4=[p1[0],p1[1],p1[2]+h]
      # Faces
      gf1 = g.entities.add_face(p1, p_bl, p_tl, p4)
      gf2 = g.entities.add_face(p_bl, p_br, p_tr, p_tl)
      gf3 = g.entities.add_face(p_br, p2, p3, p_tr)
      [gf1, gf2, gf3].compact.each do |f|
        f.material = mg
        f.reverse! if (f.normal.x * vn[0] + f.normal.y * vn[1] + f.normal.z * vn[2]) < 0
      end
      # Top and bottom caps
      g.entities.add_face(p1, p2, p_br, p_bl).pushpull(2) rescue nil # Sill
      rf = g.entities.add_face(p4, p3, p_tr, p_tl)
      rf.pushpull(-4) rescue nil if rf
      return g
    end
    
    # Create the glass and inner frame area
    if is_arch
      arch_segs = 12
      center = [p1[0]+vx[0]*(w/2.0), p1[1]+vx[1]*(w/2.0), p4[2]-arch_h]
      arch_pts = []
      (0..arch_segs).each do |i|
        ang = Math::PI - (i.to_f/arch_segs) * Math::PI
        ax = center[0] + Math.cos(ang)*vx[0]*(w/2.0)
        ay = center[1] + Math.cos(ang)*vx[1]*(w/2.0)
        az = center[2] + Math.sin(ang)*(w/2.0)
        arch_pts << [ax, ay, az]
      end
      glass_face_pts = [p1, p2] + arch_pts.reverse
    else
      glass_face_pts = [p1, p2, p3, p4]
    end
    
    # Recess everything by 2 inches
    r_pts = glass_face_pts.map { |pt| [pt[0]+vn[0]*0.2, pt[1]+vn[1]*0.2, pt[2]] }
    glass_face = g.entities.add_face(r_pts)
    glass_face.material = mg if glass_face
    
    # Outer Casing Frame
    cw = ft * 2.0; cd = ft
    cf_pts = [
      [p1[0]-vx[0]*cw, p1[1]-vx[1]*cw, p1[2]-cw],
      [p2[0]+vx[0]*cw, p2[1]+vx[1]*cw, p2[2]-cw],
      [p3[0]+vx[0]*cw, p3[1]+vx[1]*cw, p3[2]+cw],
      [p4[0]-vx[0]*cw, p4[1]-vx[1]*cw, p4[2]+cw]
    ]
    cf = g.entities.add_face(cf_pts)
    if cf
      hole = g.entities.add_face(glass_face_pts)
      hole.erase! if hole
      cf.pushpull(-cd) rescue nil
      cf.material = mw rescue nil
    end
    
    # Window Sill
    if has_sill
      sw=6.0; sd=3.0; sill_p = sp
      sf_pts = [
        [p1[0]-vx[0]*sw, p1[1]-vx[1]*sw, p1[2]-2],
        [p2[0]+vx[0]*sw, p2[1]+vx[1]*sw, p2[2]-2],
        [p2[0]+vx[0]*sw+vn[0]*sill_p, p2[1]+vx[1]*sw+vn[1]*sill_p, p2[2]-4],
        [p1[0]-vx[0]*sw+vn[0]*sill_p, p1[1]-vx[1]*sw+vn[1]*sill_p, p1[2]-4]
      ]
      sf = g.entities.add_face(sf_pts)
      sf.pushpull(-sd) rescue nil
    end
    
    # Mullions
    gw = w / panes_x.to_f
    gh = (is_arch ? h-arch_h : h) / panes_y.to_f
    m_w = mt / 2.0
    (1...panes_x).each do |i|
      mx = p1[0] + vx[0]*(i*gw)
      my = p1[1] + vx[1]*(i*gw)
      top_z = (is_arch && i == panes_x/2) ? p4[2] : p4[2]-arch_h
      mf = g.entities.add_face([mx-vx[0]*m_w, my-vx[1]*m_w, p1[2]], [mx+vx[0]*m_w, my+vx[1]*m_w, p1[2]],
                          [mx+vx[0]*m_w, my+vx[1]*m_w, top_z], [mx-vx[0]*m_w, my-vx[1]*m_w, top_z])
      if mf
        mf.reverse! if (mf.normal.x * vn[0] + mf.normal.y * vn[1] + mf.normal.z * vn[2]) < 0
        mf.pushpull(mt) rescue nil
      end
    end
    (1...panes_y).each do |i|
      mz = p1[2] + vy[2]*(i*gh)
      mf2 = g.entities.add_face([p1[0], p1[1], mz-m_w], [p2[0], p2[1], mz-m_w],
                          [p2[0], p2[1], mz+m_w], [p1[0], p1[1], mz+m_w])
      if mf2
        mf2.reverse! if (mf2.normal.x * vn[0] + mf2.normal.y * vn[1] + mf2.normal.z * vn[2]) < 0
        mf2.pushpull(mt) rescue nil
      end
    end
    
    # Louvers (Shutters)
    if has_louvers
      sh_w = w / 2.0
      sh_d = 1.5
      lv_count = (h / 4.0).to_i
      [-1, 1].each do |side|
        sx = side == -1 ? p1[0]-vx[0]*sh_w : p2[0]
        sy = side == -1 ? p1[1]-vx[1]*sh_w : p2[1]
        sz = p1[2]
        sf_pts = [
          [sx, sy, sz], [sx+vx[0]*sh_w, sy+vx[1]*sh_w, sz],
          [sx+vx[0]*sh_w, sy+vx[1]*sh_w, sz+h], [sx, sy, sz+h]
        ]
        s_face = g.entities.add_face(sf_pts)
        if s_face
          s_face.pushpull(-sh_d) rescue nil
          (1..lv_count).each do |li|
            lz = sz + li * 4.0
            # Draw angled slats
            slat_pts = [
              [sx+vx[0]*1, sy+vx[1]*1, lz],
              [sx+vx[0]*(sh_w-1), sy+vx[1]*(sh_w-1), lz],
              [sx+vx[0]*(sh_w-1)+vn[0]*1, sy+vx[1]*(sh_w-1)+vn[1]*1, lz-1.5],
              [sx+vx[0]*1+vn[0]*1, sy+vx[1]*1+vn[1]*1, lz-1.5]
            ]
            s_face_in = g.entities.add_face(slat_pts)
            s_face_in.pushpull(-0.5) rescue nil if s_face_in
          end
        end
      end
    end

    model.commit_operation
    g
  end
end

module BuildingTools
  @@blocks = {}

  # ============================================================
  # UTILITIES
  # ============================================================

  def self.clear_scene
    model = Sketchup.active_model
    model.start_operation("Clear Scene", true)
    model.entities.clear!
    @@blocks = {}
    model.commit_operation
    "Scene cleared."
  end

  def self.parse_color(c, default=[200,200,200])
    if c.is_a?(String) && c.start_with?("#") && c.length >= 7
      return [c[1..2].hex, c[3..4].hex, c[5..6].hex]
    end
    c.is_a?(Array) ? c : default
  rescue
    default
  end

  def self.block(id); @@blocks[id]; end

  # ============================================================
  # CORE - BUILD BLOCK
  # ============================================================

  def self.build_block(id, x, y, w, d, h, z=0.0, shape="rectangle")
    model = Sketchup.active_model
    model.start_operation("Block #{id}", true)
    group = model.entities.add_group
    
    if shape == "octagon"
      aw = w * 0.2928932
      ad = d * 0.2928932
      pts = [
        [x+aw, y, z], [x+w-aw, y, z],
        [x+w, y+ad, z], [x+w, y+d-ad, z],
        [x+w-aw, y+d, z], [x+aw, y+d, z],
        [x, y+d-ad, z], [x, y+ad, z]
      ]
      face = group.entities.add_face(pts)
    elsif shape == "cylinder"
      cx = x + w/2.0
      cy = y + d/2.0
      pts = (0...24).map { |i| 
        ang = i * Math::PI / 12.0
        [cx + (w/2.0)*Math.cos(ang), cy + (d/2.0)*Math.sin(ang), z]
      }
      face = group.entities.add_face(pts)
    else
      face = group.entities.add_face([x,y,z],[x+w,y,z],[x+w,y+d,z],[x,y+d,z])
    end
    
    face.reverse! if face.normal.z < 0
    face.pushpull(h)
    @@blocks[id] = { group: group, x: x, y: y, z: z, w: w, d: d, h: h, shape: shape,
                     roof_group: nil, features: [], gable_faces: [], trim_color: nil }
    model.commit_operation
    "Block #{id}: #{w}x#{d}x#{h} at Z=#{z} Shape=#{shape}"
  rescue => e; model.abort_operation; "ERROR build_block: #{e.message}"
  end

  # ============================================================
  # BASEBOARD with cap molding
  # ============================================================

  def self.add_baseboard(id, height, protrusion)
    return unless (b = @@blocks[id])
    height = 14.0 if height.to_f <= 0
    protrusion = 3.0 if protrusion.to_f <= 0
    x, y, w, d = b[:x], b[:y], b[:w], b[:d]
    model = Sketchup.active_model
    model.start_operation("Baseboard #{id}", true)
    g = model.entities.add_group
    z = b[:z] || 0.0

    if b[:shape] == "octagon" || b[:shape] == "cylinder"
      segments = (b[:shape] == "octagon") ? 8 : 24
      nx = x - protrusion; ny = y - protrusion; nw = w + 2*protrusion; nd = d + 2*protrusion
      cx = x + w/2.0; cy = y + d/2.0
      pts = []
      if b[:shape] == "octagon"
        aw = nw * 0.2928932; ad = nd * 0.2928932
        pts = [
          [nx+aw, ny, z], [nx+nw-aw, ny, z], [nx+nw, ny+ad, z], [nx+nw, ny+nd-ad, z],
          [nx+nw-aw, ny+nd, z], [nx+aw, ny+nd, z], [nx, ny+nd-ad, z], [nx, ny+ad, z]
        ]
      else
        pts = (0...24).map { |i| ang = i * Math::PI / 12.0; [cx + (nw/2.0)*Math.cos(ang), cy + (nd/2.0)*Math.sin(ang), z] }
      end
      f = g.entities.add_face(pts)
      f.reverse! if f.normal.z < 0 rescue nil
      f.pushpull(height) rescue nil
      
      # Cap molding
      p2 = protrusion + 1.5
      nx2 = x - p2; ny2 = y - p2; nw2 = w + 2*p2; nd2 = d + 2*p2
      pts2 = []
      if b[:shape] == "octagon"
        aw2 = nw2 * 0.2928932; ad2 = nd2 * 0.2928932
        pts2 = [
          [nx2+aw2, ny2, z+height], [nx2+nw2-aw2, ny2, z+height], [nx2+nw2, ny2+ad2, z+height], [nx2+nw2, ny2+nd2-ad2, z+height],
          [nx2+nw2-aw2, ny2+nd2, z+height], [nx2+aw2, ny2+nd2, z+height], [nx2, ny2+nd2-ad2, z+height], [nx2, ny2+ad2, z+height]
        ]
      else
        pts2 = (0...24).map { |i| ang = i * Math::PI / 12.0; [cx + (nw2/2.0)*Math.cos(ang), cy + (nd2/2.0)*Math.sin(ang), z+height] }
      end
      cf = g.entities.add_face(pts2)
      cf.reverse! if cf.normal.z < 0 rescue nil
      cf.pushpull(2) rescue nil
      g.name = "Baseboard"
      b[:features] << g
      model.commit_operation
      return
    end

    # Main baseboard
    z = b[:z] || 0.0
    f = g.entities.add_face([x-protrusion,y-protrusion,z],[x+w+protrusion,y-protrusion,z],
                             [x+w+protrusion,y+d+protrusion,z],[x-protrusion,y+d+protrusion,z])
    f.reverse! if f.normal.z < 0
    f.pushpull(height)
    # Cap molding
    p2 = protrusion + 1.5
    cf = g.entities.add_face([x-p2,y-p2,height],[x+w+p2,y-p2,height],
                              [x+w+p2,y+d+p2,height],[x-p2,y+d+p2,height])
    cf.pushpull(2) rescue nil
    g.name = "Baseboard"
    b[:features] << g
    model.commit_operation
  rescue => e; "ERROR baseboard: #{e.message}"
  end

  # ============================================================
  # ROOF - gable/hip with fascia thickness
  # ============================================================

  def self.build_roof(id, type, direction, pitch_deg, overhang, fascia_height=6.0)
    return unless (b = @@blocks[id])
    x, y, w, d = b[:x], b[:y], b[:w], b[:d]
    h = (b[:z] || 0.0) + b[:h]
    pr = pitch_deg * Math::PI / 180.0
    tv = fascia_height
    model = Sketchup.active_model
    model.start_operation("Roof #{id}", true)
    g = model.entities.add_group

    is_chinese = false
    if type == "chinese_hip"
      is_chinese = true
      type = "hip"
      overhang = [overhang, 48.0].max
      pitch_deg = [pitch_deg, 40.0].max
      pr = pitch_deg * Math::PI / 180.0
      tv = 8.0
    end

    if b[:shape] == "octagon" || b[:shape] == "cylinder"
      segments = (b[:shape] == "octagon") ? 8 : 24
      nx = x - overhang; ny = y - overhang; nw = w + 2*overhang; nd = d + 2*overhang
      cx = x + w/2.0; cy = y + d/2.0
      
      pts = []
      if b[:shape] == "octagon"
        aw = nw * 0.2928932; ad = nd * 0.2928932
        pts = [
          [nx+aw, ny, h], [nx+nw-aw, ny, h], [nx+nw, ny+ad, h], [nx+nw, ny+nd-ad, h],
          [nx+nw-aw, ny+nd, h], [nx+aw, ny+nd, h], [nx, ny+nd-ad, h], [nx, ny+ad, h]
        ]
      else
        pts = (0...24).map { |i| ang = i * Math::PI / 12.0; [cx + (nw/2.0)*Math.cos(ang), cy + (nd/2.0)*Math.sin(ang), h] }
      end
      
      sweep_h = is_chinese ? 24.0 : 0.0
      flare_out = is_chinese ? 16.0 : 0.0
      
      pts_corners = []
      base_corners = []
      pts_mids = []
      base_mids = []
      
      (0...segments).each do |i|
         p1 = pts[i]
         p2 = pts[(i+1)%segments]
         
         dx = p1[0] - cx
         dy = p1[1] - cy
         dist = Math.sqrt(dx*dx + dy*dy)
         ndx = dx / dist * flare_out
         ndy = dy / dist * flare_out
         
         pts_corners << [p1[0] + ndx, p1[1] + ndy, h + sweep_h]
         base_corners << [p1[0] + ndx, p1[1] + ndy, h - tv + sweep_h]
         
         pts_mids << [(p1[0]+p2[0])/2.0, (p1[1]+p2[1])/2.0, h]
         base_mids << [(p1[0]+p2[0])/2.0, (p1[1]+p2[1])/2.0, h - tv]
      end
      
      rh = (nw/2.0) * Math.tan(pr)
      apex = [cx, cy, h + rh]
      
      (0...segments).each do |i|
        c1 = pts_corners[i]
        c2 = pts_corners[(i+1)%segments]
        m1 = pts_mids[i]
        
        bc1 = base_corners[i]
        bc2 = base_corners[(i+1)%segments]
        bm1 = base_mids[i]
        
        if is_chinese
          # Triangulated fascia
          g.entities.add_face(bc1, bm1, m1) rescue nil
          g.entities.add_face(bc1, m1, c1) rescue nil
          g.entities.add_face(bm1, bc2, c2) rescue nil
          g.entities.add_face(bm1, c2, m1) rescue nil
          
          # Triangulated roof
          g.entities.add_face(c1, m1, apex) rescue nil
          g.entities.add_face(m1, c2, apex) rescue nil
          
          # Triangulated bottom
          g.entities.add_face([cx, cy, h - tv], bc1, bm1) rescue nil
          g.entities.add_face([cx, cy, h - tv], bm1, bc2) rescue nil
        else
          g.entities.add_face(bc1, bc2, c2, c1) rescue nil
          g.entities.add_face(c1, c2, apex) rescue nil
          g.entities.add_face([cx, cy, h - tv], bc1, bc2) rescue nil
        end
      end
      
      b[:roof_group] = g
      model.commit_operation
      return
    end

    if type == "hip"
      # Fascia box
      ff = g.entities.add_face([x-overhang,y-overhang,h-tv],[x+w+overhang,y-overhang,h-tv],
                                [x+w+overhang,y+d+overhang,h-tv],[x-overhang,y+d+overhang,h-tv])
      ff.reverse! if ff.normal.z < 0
      ff.pushpull(tv)
      
      shorter = [w, d].min
      rh = (shorter/2.0) * Math.tan(pr)
      if w >= d # ridge runs left-right
        rx1 = x + overhang + shorter/2.0
        rx2 = x + w + overhang - shorter/2.0
        ry = y + d/2.0
        g.entities.add_face([x-overhang,y-overhang,h],[x+w+overhang,y-overhang,h],[rx2,ry,h+rh],[rx1,ry,h+rh])
        g.entities.add_face([x+w+overhang,y-overhang,h],[x+w+overhang,y+d+overhang,h],[rx2,ry,h+rh])
        g.entities.add_face([x+w+overhang,y+d+overhang,h],[x-overhang,y+d+overhang,h],[rx1,ry,h+rh],[rx2,ry,h+rh])
        g.entities.add_face([x-overhang,y+d+overhang,h],[x-overhang,y-overhang,h],[rx1,ry,h+rh])
      else # ridge runs front-back
        ry1 = y + overhang + shorter/2.0
        ry2 = y + d + overhang - shorter/2.0
        cx = x + w/2.0
        g.entities.add_face([x-overhang,y-overhang,h],[x+w+overhang,y-overhang,h],[cx,ry1,h+rh])
        g.entities.add_face([x+w+overhang,y-overhang,h],[x+w+overhang,y+d+overhang,h],[cx,ry2,h+rh],[cx,ry1,h+rh])
        g.entities.add_face([x+w+overhang,y+d+overhang,h],[x-overhang,y+d+overhang,h],[cx,ry2,h+rh])
        g.entities.add_face([x-overhang,y+d+overhang,h],[x-overhang,y-overhang,h],[cx,ry1,h+rh],[cx,ry2,h+rh])
      end

    elsif type == "flat" || type == "shed"
      f = g.entities.add_face([x-overhang,y-overhang,h],[x+w+overhang,y-overhang,h],
                               [x+w+overhang,y+d+overhang,h],[x-overhang,y+d+overhang,h])
      f.reverse! if f.normal.z < 0
      f.pushpull(14)

    else # gable
      if direction == "front-back"
        rh = (w/2.0) * Math.tan(pr)
        # Left roof slab
        f1 = g.entities.add_face([x-overhang, y-overhang, h], [x+w/2.0, y-overhang, h+rh], 
                                 [x+w/2.0, y-overhang, h+rh-tv], [x-overhang, y-overhang, h-tv])
        f1.reverse! if f1.normal.y < 0
        f1.pushpull(d + 2*overhang) rescue nil
        
        # Right roof slab
        f2 = g.entities.add_face([x+w+overhang, y-overhang, h], [x+w/2.0, y-overhang, h+rh], 
                                 [x+w/2.0, y-overhang, h+rh-tv], [x+w+overhang, y-overhang, h-tv])
        f2.reverse! if f2.normal.y < 0
        f2.pushpull(d + 2*overhang) rescue nil
        
        # Gable wall triangles (at wall face, body color)
        b[:gable_faces] << b[:group].entities.add_face([x,y,h],[x+w,y,h],[x+w/2.0,y,h+rh])
        b[:gable_faces] << b[:group].entities.add_face([x,y+d,h],[x+w,y+d,h],[x+w/2.0,y+d,h+rh])
      else
        rh = (d/2.0) * Math.tan(pr)
        # Front roof slab
        f1 = g.entities.add_face([x-overhang, y-overhang, h], [x-overhang, y+d/2.0, h+rh],
                                 [x-overhang, y+d/2.0, h+rh-tv], [x-overhang, y-overhang, h-tv])
        f1.reverse! if f1.normal.x < 0
        f1.pushpull(w + 2*overhang) rescue nil
        
        # Back roof slab
        f2 = g.entities.add_face([x-overhang, y+d+overhang, h], [x-overhang, y+d/2.0, h+rh],
                                 [x-overhang, y+d/2.0, h+rh-tv], [x-overhang, y+d+overhang, h-tv])
        f2.reverse! if f2.normal.x < 0
        f2.pushpull(w + 2*overhang) rescue nil
        
        # Gable wall triangles (at wall face, body color)
        b[:gable_faces] << b[:group].entities.add_face([x,y,h],[x,y+d,h],[x,y+d/2.0,h+rh])
        b[:gable_faces] << b[:group].entities.add_face([x+w,y,h],[x+w,y+d,h],[x+w,y+d/2.0,h+rh])
      end
    end

    # Roof Texturing (Shingle Lines)
    # Give the roof some horizontal lines to simulate shingles or seams.
    begin
      g.entities.grep(Sketchup::Face).each do |face|
        next if face.normal.z < 0.1 # Skip bottom faces (fascia)
        # Find Z range
        zs = face.vertices.map { |v| v.position.z }
        zmin, zmax = zs.min, zs.max
        next if zmax - zmin < 12.0 # Skip flat roofs or very low pitch
        # Draw horizontal lines every 16 inches
        z_curr = zmin + 16.0
        while z_curr < zmax
          p = face.plane
          # A horizontal plane at z = z_curr: [0, 0, 1, -z_curr]
          line = Geom.intersect_plane_plane(p, [0, 0, 1, -z_curr])
          if line
            # Intersect infinite line with face bounds? It's easier to just offset the bottom edge, 
            # but drawing lines directly on face via ruby requires cutting.
            # SketchUp Ruby doesn't easily let us draw shingle lines on faces without complex intersections.
            # I will skip the geometry lines to avoid crash, and we rely on material applying later.
          end
          z_curr += 16.0
        end
      end
    rescue => ex; end

    b[:roof_group] = g
    model.commit_operation
    "Roof #{type}/#{direction} for #{id}"
  rescue => e; "ERROR build_roof: #{e.message}"
  end

  # ============================================================
  # CHIMNEY - detailed with cap + crown
  # ============================================================

  def self.build_chimney(id, cx, cy, cw, cd, ch)
    return unless (b = @@blocks[id])
    x, y, w, d, h = b[:x], b[:y], b[:w], b[:d], b[:h]
    sx = x + w*cx - cw/2.0; sy = y + d*cy - cd/2.0
    model = Sketchup.active_model
    model.start_operation("Chimney #{id}", true)
    g = model.entities.add_group
    # Shaft
    f = g.entities.add_face([sx,sy,h],[sx+cw,sy,h],[sx+cw,sy+cd,h],[sx,sy+cd,h])
    f.reverse! if f.normal.z < 0; f.pushpull(ch)
    # Crown molding
    ext = 2.5
    cf = g.entities.add_face([sx-ext,sy-ext,h+ch],[sx+cw+ext,sy-ext,h+ch],
                              [sx+cw+ext,sy+cd+ext,h+ch],[sx-ext,sy+cd+ext,h+ch])
    cf.pushpull(4) rescue nil
    # Chimney pot
    px = sx + cw/2.0 - 4; py = sy + cd/2.0 - 4
    pf = g.entities.add_face([px,py,h+ch+4],[px+8,py,h+ch+4],[px+8,py+8,h+ch+4],[px,py+8,h+ch+4])
    pf.reverse! if pf.normal.z < 0; pf.pushpull(16) rescue nil
    b[:features] << g
    model.commit_operation
  rescue => e; "ERROR chimney: #{e.message}"
  end

  # ============================================================
  # WINDOW - with casing, sill, mullions, glazing bars
  # ============================================================

  def self.add_window(id, face_name, xo, zo, w, h, panes_x, panes_y, style="rectangular", has_sill=true, has_louvers=false, ft=2.0, mt=1.0, sp=2.0)
    return unless (b = @@blocks[id])
    bx, by, bw, bd, bh = b[:x], b[:y], b[:w], b[:d], b[:h]
    bz = b[:z] || 0.0
    
    face_len = (face_name == "front" || face_name == "back") ? bw : bd
    if xo < 0 || xo + w > face_len
      raise "Logical Error: Window (width: #{w}) at x_offset #{xo} exceeds the #{face_name} wall's width (#{face_len})."
    end
    # 1. Z-Height Auto-Snapping Algorithm (Golden Ratio)
    if (zo - 36).abs < 15; zo = 36; end   # 1st floor
    if (zo - 136).abs < 15; zo = 136; end # 2nd floor
    if (zo - 236).abs < 15; zo = 236; end # 3rd floor
    
    # 2. Gable Triangle Fix: Allow windows in attic
    max_h = bh * 1.6 # Allow 60% taller for gable ends
    if zo < bz || zo + h > bz + max_h
      raise "Logical Error: Window (height: #{h}) at z_offset #{zo} exceeds the gable roof height limit (#{bz + max_h})."
    end
    
    case face_name
    when "front" then p1=[bx+xo,by,zo]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then p1=[bx+bw-xo,by+bd,zo]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then p1=[bx,by+bd-xo,zo]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then p1=[bx+bw,by+xo,zo]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return "ERROR: bad face"
    end
    
    p2 = [p1[0]+vx[0]*w, p1[1]+vx[1]*w, p1[2]]
    p3 = [p2[0], p2[1], p2[2]+h]
    p4 = [p1[0], p1[1], p1[2]+h]
    
    begin
      if b[:group]
        # Create a temp group with the window footprint
        temp_g = Sketchup.active_model.active_entities.add_group
        temp_g.entities.add_face(p1, p2, p3, p4)
        
        # Intersect with the wall to force splitting the wall face
        b[:group].entities.intersect_with(false, b[:group].transformation, b[:group].entities, temp_g.transformation, false, temp_g)
        temp_g.erase!
        
        # Ensure the inner face is fully formed
        e1 = b[:group].entities.add_line(p1, p2)
        b[:group].entities.add_line(p2, p3)
        b[:group].entities.add_line(p3, p4)
        b[:group].entities.add_line(p4, p1)
        e1.find_faces
        
        # Erase ALL faces whose vertices are entirely within the window footprint
        min_x = [p1.x, p2.x, p3.x, p4.x].min - 0.2
        max_x = [p1.x, p2.x, p3.x, p4.x].max + 0.2
        min_y = [p1.y, p2.y, p3.y, p4.y].min - 0.2
        max_y = [p1.y, p2.y, p3.y, p4.y].max + 0.2
        min_z = [p1.z, p2.z, p3.z, p4.z].min - 0.2
        max_z = [p1.z, p2.z, p3.z, p4.z].max + 0.2
        
        faces_to_erase = []
        b[:group].entities.grep(Sketchup::Face).each do |f|
          # Only erase faces that are on the same plane as the window!
          # For 'front' face, normal is roughly [0, -1, 0]. But checking bounding box is enough.
          is_inside = true
          f.vertices.each do |v|
            pt = v.position
            unless pt.x >= min_x && pt.x <= max_x && pt.y >= min_y && pt.y <= max_y && pt.z >= min_z && pt.z <= max_z
              is_inside = false
              break
            end
          end
          faces_to_erase << f if is_inside
        end
        faces_to_erase.each { |f| f.erase! if f.valid? }
      end
    rescue => e
      puts "Warning: Could not cut hole for window: #{e.message}"
    end
    
    g = ParametricWindow.generate(p1, vx, vy, vn, w, h, panes_x, panes_y, style, has_sill, has_louvers, ft, mt, sp)
    g.name = "ParametricWindow" if g
    b[:features] << g if g
  rescue => e; "ERROR window: #{e.message}"
  end

  def self.add_door(id, face_name, x, w, h, style="solid", panes_x=1, panes_y=1, arch_top=false, has_transom=false, fd=2.0, lr=2.0)
    return unless (b = @@blocks[id])
    bx, by, bz, bw, bd, bh = b[:x], b[:y], 0, b[:w], b[:d], b[:h]
    
    face_len = (face_name == "front" || face_name == "back") ? bw : bd
    if x < 0 || x + w > face_len
      raise "Logical Error: Door (width: #{w}) at x_offset #{x} exceeds the #{face_name} wall's width (#{face_len})."
    end
    if h > bh
      raise "Logical Error: Door (height: #{h}) exceeds the wall's height (#{bh})."
    end
    
    case face_name
    when "front" then p1=[bx+x,by,bz]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then p1=[bx+bw-x,by+bd,bz]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then p1=[bx,by+bd-x,bz]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then p1=[bx+bw,by+x,bz]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return "ERROR: bad face"
    end
    
    p2 = [p1[0]+vx[0]*w, p1[1]+vx[1]*w, p1[2]]
    p3 = [p2[0], p2[1], p2[2]+h]
    p4 = [p1[0], p1[1], p1[2]+h]
    
    begin
      if b[:group]
        # Create a temp group with the door footprint
        temp_g = Sketchup.active_model.active_entities.add_group
        temp_g.entities.add_face(p1, p2, p3, p4)
        
        # Intersect with the wall to force splitting the wall face
        b[:group].entities.intersect_with(false, b[:group].transformation, b[:group].entities, temp_g.transformation, false, temp_g)
        temp_g.erase!
        
        # Ensure the inner face is fully formed
        e1 = b[:group].entities.add_line(p1, p2)
        b[:group].entities.add_line(p2, p3)
        b[:group].entities.add_line(p3, p4)
        b[:group].entities.add_line(p4, p1)
        e1.find_faces
        
        # Erase ALL faces whose vertices are entirely within the door footprint
        min_x = [p1.x, p2.x, p3.x, p4.x].min - 0.2
        max_x = [p1.x, p2.x, p3.x, p4.x].max + 0.2
        min_y = [p1.y, p2.y, p3.y, p4.y].min - 0.2
        max_y = [p1.y, p2.y, p3.y, p4.y].max + 0.2
        min_z = [p1.z, p2.z, p3.z, p4.z].min - 0.2
        max_z = [p1.z, p2.z, p3.z, p4.z].max + 0.2
        
        faces_to_erase = []
        b[:group].entities.grep(Sketchup::Face).each do |f|
          is_inside = true
          f.vertices.each do |v|
            pt = v.position
            unless pt.x >= min_x && pt.x <= max_x && pt.y >= min_y && pt.y <= max_y && pt.z >= min_z && pt.z <= max_z
              is_inside = false
              break
            end
          end
          faces_to_erase << f if is_inside
        end
        faces_to_erase.each { |f| f.erase! if f.valid? }
      end
    rescue => e
      Sketchup.active_model.entities.add_3d_text("Hole Err: " + e.message, TextAlignLeft, "Arial", true, false, 10.0, 0.0, 0.0, true, 0.0)
    end
    
    begin
      g = ParametricDoor.generate(p1, vx, vy, vn, w, h, style, panes_x, panes_y, arch_top, has_transom, fd, lr)
      if g
        g.name = (style.include?("garage") ? "ParametricGarageDoor" : "ParametricDoor")
        b[:features] << g
      end
    rescue => e
      # Draw 3D text at the door location!
      tg = Sketchup.active_model.entities.add_group
      tg.entities.add_3d_text("Err: " + e.message, TextAlignLeft, "Arial", true, false, 5.0, 0.0, 0.0, true, 0.0)
      tg.transformation = Geom::Transformation.translation(Geom::Vector3d.new(p1[0], p1[1]-10, p1[2]+h/2.0))
    end
  rescue => e; "ERROR door: #{e.message}"
  end

  def self.add_columns(id, face_name, x_start, x_end, num_cols, col_height, style="round")
    return unless (b = @@blocks[id])
    bx, by, bw, bd, bh = b[:x], b[:y], b[:w], b[:d], b[:h]
    
    spacing = (x_end - x_start) / [num_cols-1, 1].max.to_f
    case face_name
    when "front" then cy = by; cx_base = bx + x_start; cv = [1,0,0]; cn = [0,-1,0]
    when "back"  then cy = by+bd; cx_base = bx+bw-x_start; cv = [-1,0,0]; cn = [0,1,0]
    when "left"  then cy = bx; cx_base = by+bd-x_start; cv = [0,-1,0]; cn = [-1,0,0]
    when "right" then cy = bx+bw; cx_base = by+x_start; cv = [0,1,0]; cn = [1,0,0]
    else return
    end

    (0...num_cols).each do |i|
      cx = cx_base + (face_name=="front"||face_name=="back" ? cv[0]*spacing*i : 0)
      cy_actual = (face_name=="left"||face_name=="right" ? cx_base + cv[1]*spacing*i : cy)
      cx_actual = (face_name=="left"||face_name=="right" ? cy : cx) # swapped because cy holds the constant axis
      
      g = ParametricColumn.generate(cx_actual, cy_actual, cn, col_height, style)
      g.name = "ParametricColumn" if g
      b[:features] << g if g
    end
  rescue => e; "ERROR columns: #{e.message}"
  end

  def self.add_dormer(id, face_name, xo, zo, w, h, style="gable", window_style="rectangular")
    return unless (b = @@blocks[id])
    bx, by, bz, bw, bd, bh = b[:x], b[:y], 0, b[:w], b[:d], b[:h]
    zo = bh # Force z_offset to the eave height so it sits on the roof edge
    case face_name
    when "front" then p1=[bx+xo,by,zo]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then p1=[bx+bw-xo,by+bd,zo]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then p1=[bx,by+bd-xo,zo]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then p1=[bx+bw,by+xo,zo]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return "ERROR: bad face"
    end
    
    g = ParametricDormer.generate(p1, vx, vy, vn, w, h, style, window_style)
    g.name = "ParametricDormer" if g
    b[:features] << g if g
  rescue => e; "ERROR dormer: #{e.message}"
  end

  def self.add_canopy(id, face_name, xo, zo, w, d, style="gable", support_style="brackets")
    return unless (b = @@blocks[id])
    bx, by, bz, bw, bd = b[:x], b[:y], 0, b[:w], b[:d]
    case face_name
    when "front" then p1=[bx+xo,by,zo]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then p1=[bx+bw-xo,by+bd,zo]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then p1=[bx,by+bd-xo,zo]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then p1=[bx+bw,by+xo,zo]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return "ERROR: bad face"
    end
    
    g = ParametricCanopy.generate(p1, vx, vy, vn, w, d, style, support_style)
    g.name = "ParametricCanopy" if g
    b[:features] << g if g
  rescue => e; "ERROR canopy: #{e.message}"
  end

  def self.add_arch(id, face_name, xo, w, spring_h, arch_type)
    return unless (b = @@blocks[id])
    bx, by, bw, bd = b[:x], b[:y], b[:w], b[:d]
    case face_name
    when "front" then origin=[bx+xo, by, spring_h]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then origin=[bx+bw-xo, by+bd, spring_h]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then origin=[bx, by+bd-xo, spring_h]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then origin=[bx+bw, by+xo, spring_h]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return
    end
    model = Sketchup.active_model
    model.start_operation("Arch #{id}", true)
    g = model.entities.add_group
    segs = 12; r = w/2.0; cx_pt = [origin[0]+vx[0]*r, origin[1]+vx[1]*r, origin[2]]
    arch_pts = [origin]
    (0..segs).each do |s|
      ang = s * Math::PI / segs
      ax = cx_pt[0] + vx[0]*r*Math.cos(Math::PI - ang)
      ay = cx_pt[1] + vx[1]*r*Math.cos(Math::PI - ang)
      az = origin[2] + vy[2]*r*Math.sin(ang)
      arch_pts << [ax, ay, az]
    end
    arch_pts << [origin[0]+vx[0]*w, origin[1]+vx[1]*w, origin[2]]
    arch_pts << origin
    af = g.entities.add_face(arch_pts) rescue nil
    af.pushpull(4) rescue nil if af
    g.name = "Arch"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR arch: #{e.message}"
  end

  # ============================================================
  # BALCONY - floor slab + railing system
  # ============================================================

  def self.add_balcony(id, face_name, xo, zo, w, depth, rail_style)
    return unless (b = @@blocks[id])
    bx, by, bw, bd = b[:x], b[:y], b[:w], b[:d]
    case face_name
    when "front" then fp=[bx+xo,by,zo]; vx=[1,0,0]; vout=[0,-1,0]
    when "back"  then fp=[bx+bw-xo,by+bd,zo]; vx=[-1,0,0]; vout=[0,1,0]
    when "left"  then fp=[bx,by+bd-xo,zo]; vx=[0,-1,0]; vout=[-1,0,0]
    when "right" then fp=[bx+bw,by+xo,zo]; vx=[0,1,0]; vout=[1,0,0]
    else return
    end

    model = Sketchup.active_model
    model.start_operation("Balcony #{id}", true)
    g = model.entities.add_group
    slab_t = 8.0; rail_h = 36.0; rail_t = 3.0; post_w = 3.0

    if b[:shape] == "octagon" || b[:shape] == "cylinder"
      segments = (b[:shape] == "octagon") ? 8 : 24
      nx = bx - depth; ny = by - depth; nw = bw + 2*depth; nd = bd + 2*depth
      cx = bx + bw/2.0; cy = by + bd/2.0
      
      pts = []
      if b[:shape] == "octagon"
        aw = nw * 0.2928932; ad = nd * 0.2928932
        pts = [
          [nx+aw, ny, zo], [nx+nw-aw, ny, zo], [nx+nw, ny+ad, zo], [nx+nw, ny+nd-ad, zo],
          [nx+nw-aw, ny+nd, zo], [nx+aw, ny+nd, zo], [nx, ny+nd-ad, zo], [nx, ny+ad, zo]
        ]
      else
        pts = (0...24).map { |i| ang = i * Math::PI / 12.0; [cx + (nw/2.0)*Math.cos(ang), cy + (nd/2.0)*Math.sin(ang), zo] }
      end
      
      sf = g.entities.add_face(pts)
      sf.reverse! if sf.normal.z < 0 rescue nil
      sf.pushpull(slab_t) rescue nil
      
      # Draw railings
      pts_top = pts.map { |pt| [pt[0], pt[1], zo + slab_t + rail_h] }
      pts_bot = pts.map { |pt| [pt[0], pt[1], zo + slab_t] }
      
      (0...segments).each do |i|
        nxt = (i+1)%segments
        # Top rail
        r_f = g.entities.add_face([pts_top[i], pts_top[nxt], 
                                   [pts_top[nxt][0], pts_top[nxt][1], pts_top[nxt][2]-rail_t], 
                                   [pts_top[i][0], pts_top[i][1], pts_top[i][2]-rail_t]]) rescue nil
        r_f.pushpull(-rail_t) rescue nil
        
        # Balusters
        p1 = pts_bot[i]; p2 = pts_bot[nxt]
        dist = Math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        n_bal = (dist / 8.0).to_i
        n_bal.times do |k|
          next if k==0
          frac = k.to_f / n_bal
          bx = p1[0] + (p2[0]-p1[0])*frac
          by = p1[1] + (p2[1]-p1[1])*frac
          b_f = g.entities.add_face([bx-1,by-1,zo+slab_t], [bx+1,by-1,zo+slab_t], [bx+1,by+1,zo+slab_t], [bx-1,by+1,zo+slab_t]) rescue nil
          b_f.pushpull(rail_h) rescue nil
        end
      end
      
      b[:features] << g
      model.commit_operation
      return
    end
    model = Sketchup.active_model
    model.start_operation("Balcony #{id}", true)
    g = model.entities.add_group
    slab_t = 8.0; rail_h = 36.0; rail_t = 3.0; post_w = 3.0

    # Floor slab
    sp1=fp; sp2=[fp[0]+vx[0]*w,fp[1]+vx[1]*w,fp[2]]
    sp3=[sp2[0]+vout[0]*depth,sp2[1]+vout[1]*depth,sp2[2]]
    sp4=[sp1[0]+vout[0]*depth,sp1[1]+vout[1]*depth,sp1[2]]
    sf = g.entities.add_face(sp1,sp2,sp3,sp4)
    sf.reverse! if sf.normal.z < 0
    sf.pushpull(slab_t)

    rail_z = zo + slab_t
    # Front rail
    rp1=[sp1[0]+vout[0]*depth,sp1[1]+vout[1]*depth,rail_z]
    rp2=[sp2[0]+vout[0]*depth,sp2[1]+vout[1]*depth,rail_z]
    rf = g.entities.add_face(rp1,rp2,[rp2[0],rp2[1],rp2[2]+rail_h],[rp1[0],rp1[1],rp1[2]+rail_h])
    rf.pushpull(rail_t) rescue nil

    # Side rails
    [sp1, sp2].each do |corner|
      sr1=[corner[0],corner[1],rail_z]
      sr2=[corner[0]+vout[0]*depth,corner[1]+vout[1]*depth,rail_z]
      srf = g.entities.add_face(sr1,sr2,[sr2[0],sr2[1],sr2[2]+rail_h],[sr1[0],sr1[1],sr1[2]+rail_h])
      srf.pushpull(rail_t) rescue nil
    end

    # Top handrail cap
    hr_ext = 2.0
    hr1=[rp1[0]-vx[0]*hr_ext-vout[0]*hr_ext,rp1[1]-vx[1]*hr_ext-vout[1]*hr_ext,rail_z+rail_h]
    hr2=[rp2[0]+vx[0]*hr_ext-vout[0]*hr_ext,rp2[1]+vx[1]*hr_ext-vout[1]*hr_ext,rail_z+rail_h]
    hr3=[rp2[0]+vx[0]*hr_ext,rp2[1]+vx[1]*hr_ext,rail_z+rail_h]
    hr4=[rp1[0]-vx[0]*hr_ext,rp1[1]-vx[1]*hr_ext,rail_z+rail_h]
    hrf = g.entities.add_face(hr1,hr2,hr3,hr4)
    hrf.pushpull(3) rescue nil

    if rail_style == "baluster"
      # Individual balusters
      num_bal = [(w/8.0).floor, 2].max
      bal_spacing = w / num_bal.to_f
      (0..num_bal).each do |bi|
        bx2 = fp[0]+vx[0]*bi*bal_spacing; by2 = fp[1]+vx[1]*bi*bal_spacing
        bf = g.entities.add_face([bx2-1,by2+vout[1]*depth-1,rail_z],
                                  [bx2+1,by2+vout[1]*depth-1,rail_z],
                                  [bx2+1,by2+vout[1]*depth+1,rail_z],
                                  [bx2-1,by2+vout[1]*depth+1,rail_z])
        bf.pushpull(rail_h-3) rescue nil
      end
    end

    g.name = "Balcony"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR balcony: #{e.message}"
  end

  # ============================================================
  # PORCH - entry canopy with posts
  # ============================================================

  def self.add_porch(id, face_name, xo, w, depth, style)
    return unless (b = @@blocks[id])
    bx, by, bw, bd, bh = b[:x], b[:y], b[:w], b[:d], b[:h]
    case face_name
    when "front" then fp=[bx+xo,by,0]; vx=[1,0,0]; vout=[0,-1,0]
    when "back"  then fp=[bx+bw-xo,by+bd,0]; vx=[-1,0,0]; vout=[0,1,0]
    when "left"  then fp=[bx,by+bd-xo,0]; vx=[0,-1,0]; vout=[-1,0,0]
    when "right" then fp=[bx+bw,by+xo,0]; vx=[0,1,0]; vout=[1,0,0]
    else return
    end
    model = Sketchup.active_model
    model.start_operation("Porch #{id}", true)
    g = model.entities.add_group
    porch_h = bh * 0.6; col_r = 5.0; roof_t = 8.0

    # Floor deck
    pp1=fp; pp2=[fp[0]+vx[0]*w,fp[1]+vx[1]*w,fp[2]]
    pp3=[pp2[0]+vout[0]*depth,pp2[1]+vout[1]*depth,pp2[2]]
    pp4=[pp1[0]+vout[0]*depth,pp1[1]+vout[1]*depth,pp1[2]]
    pf = g.entities.add_face(pp1,pp2,pp3,pp4)
    pf.reverse! if pf.normal.z < 0
    pf.pushpull(6)

    # Posts at outer corners
    [[pp3,pp4],[pp3,pp3],[pp4,pp4]].each_with_index do |(pt,_), idx|
      post_pt = (idx==0 ? pp4 : (idx==1 ? pp3 : pp4))
      pof = g.entities.add_face([post_pt[0]-col_r,post_pt[1]-col_r,0],
                                  [post_pt[0]+col_r,post_pt[1]-col_r,0],
                                  [post_pt[0]+col_r,post_pt[1]+col_r,0],
                                  [post_pt[0]-col_r,post_pt[1]+col_r,0])
      pof.reverse! if pof.normal.z < 0
      pof.pushpull(porch_h) rescue nil
    end

    # Canopy roof
    cr_p = 12.0
    rp1=[pp4[0]-vout[0]*cr_p-vx[0]*cr_p,pp4[1]-vout[1]*cr_p-vx[1]*cr_p,porch_h]
    rp2=[pp3[0]-vout[0]*cr_p+vx[0]*cr_p,pp3[1]-vout[1]*cr_p+vx[1]*cr_p,porch_h]
    rp3=[fp[0]+vx[0]*w+vx[0]*cr_p,fp[1]+vx[1]*w+vx[1]*cr_p,porch_h]
    rp4=[fp[0]-vx[0]*cr_p,fp[1]-vx[1]*cr_p,porch_h]
    
    roof_grp = g.entities.add_group
    roof_grp.name = "PorchRoof"
    rf = roof_grp.entities.add_face(rp1,rp2,rp3,rp4)
    rf.reverse! if rf.normal.z < 0
    rf.pushpull(roof_t) rescue nil

    g.name = "Porch"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR porch: #{e.message}"
  end

  # ============================================================
  # VERANDA / CONTINUOUS PORCH
  # ============================================================

  def self.add_veranda(id, face_name, xo, w, depth, v_height, style)
    return unless (b = @@blocks[id])
    bx, by, bw, bd, bh = b[:x], b[:y], b[:w], b[:d], b[:h]
    case face_name
    when "front" then fp=[bx+xo,by,0]; vx=[1,0,0]; vout=[0,-1,0]; vn=[0,-1,0]
    when "back"  then fp=[bx+bw-xo,by+bd,0]; vx=[-1,0,0]; vout=[0,1,0]; vn=[0,1,0]
    when "left"  then fp=[bx,by+bd-xo,0]; vx=[0,-1,0]; vout=[-1,0,0]; vn=[-1,0,0]
    when "right" then fp=[bx+bw,by+xo,0]; vx=[0,1,0]; vout=[1,0,0]; vn=[1,0,0]
    else return
    end
    model = Sketchup.active_model
    model.start_operation("Veranda #{id}", true)
    g = model.entities.add_group
    
    # Floor deck
    deck_h = 10.0
    pp1=fp; pp2=[fp[0]+vx[0]*w,fp[1]+vx[1]*w,fp[2]]
    pp3=[pp2[0]+vout[0]*depth,pp2[1]+vout[1]*depth,pp2[2]]
    pp4=[pp1[0]+vout[0]*depth,pp1[1]+vout[1]*depth,pp1[2]]
    pf = g.entities.add_face(pp1,pp2,pp3,pp4)
    pf.reverse! if pf.normal.z < 0
    pf.pushpull(deck_h) rescue nil

    # Columns
    col_w = 6.0
    num_cols = [(w / 96.0).round + 1, 2].max
    spacing = w / (num_cols - 1).to_f
    (0...num_cols).each do |i|
      cx = pp4[0] + vx[0]*(spacing*i)
      cy = pp4[1] + vx[1]*(spacing*i)
      cf = g.entities.add_face([cx-col_w/2,cy-col_w/2,deck_h], [cx+col_w/2,cy-col_w/2,deck_h],
                               [cx+col_w/2,cy+col_w/2,deck_h], [cx-col_w/2,cy+col_w/2,deck_h])
      cf.reverse! if cf.normal.z < 0
      cf.pushpull(v_height - deck_h) rescue nil
    end

    # Roof (Shed style)
    roof_t = 8.0
    overhang = 12.0
    rp1 = [pp4[0]-vx[0]*overhang-vout[0]*overhang, pp4[1]-vx[1]*overhang-vout[1]*overhang, v_height]
    rp2 = [pp3[0]+vx[0]*overhang-vout[0]*overhang, pp3[1]+vx[1]*overhang-vout[1]*overhang, v_height]
    rp3 = [fp[0]+vx[0]*w+vx[0]*overhang, fp[1]+vx[1]*w+vx[1]*overhang, v_height + (depth * 0.3)]
    rp4 = [fp[0]-vx[0]*overhang, fp[1]-vx[1]*overhang, v_height + (depth * 0.3)]
    
    roof_grp = g.entities.add_group
    roof_grp.name = "VerandaRoof"
    rf = roof_grp.entities.add_face(rp1,rp2,rp3,rp4)
    rf.reverse! if rf.normal.z < 0
    rf.pushpull(roof_t) rescue nil

    g.name = "Veranda"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR veranda: #{e.message}"
  end

  # ============================================================
  # BELT COURSE - horizontal string course / floor band
  # ============================================================

  def self.add_belt_course(id, z_height, protrusion, course_h)
    return unless (b = @@blocks[id])
    x, y, w, d = b[:x], b[:y], b[:w], b[:d]
    protrusion = 2.5 if protrusion.to_f <= 0
    course_h = 4.0 if course_h.to_f <= 0
    model = Sketchup.active_model
    model.start_operation("BeltCourse #{id}", true)
    g = model.entities.add_group
    p2 = protrusion
    f = g.entities.add_face([x-p2,y-p2,z_height],[x+w+p2,y-p2,z_height],
                             [x+w+p2,y+d+p2,z_height],[x-p2,y+d+p2,z_height])
    f.reverse! if f.normal.z < 0
    f.pushpull(course_h)
    g.name = "BeltCourse"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR belt_course: #{e.message}"
  end

  # ============================================================
  # PILASTERS - flat engaged columns on facade
  # ============================================================

  def self.add_pilasters(id, face_name, num, depth_out, pil_w)
    return unless (b = @@blocks[id])
    bx, by, bw, bd, bh = b[:x], b[:y], b[:w], b[:d], b[:h]
    case face_name
    when "front" then start_pt=[bx,by,0]; len=bw; vx=[1,0,0]; vout=[0,-1,0]
    when "back"  then start_pt=[bx+bw,by+bd,0]; len=bw; vx=[-1,0,0]; vout=[0,1,0]
    when "left"  then start_pt=[bx,by+bd,0]; len=bd; vx=[0,-1,0]; vout=[-1,0,0]
    when "right" then start_pt=[bx+bw,by,0]; len=bd; vx=[0,1,0]; vout=[1,0,0]
    else return
    end
    model = Sketchup.active_model
    model.start_operation("Pilasters #{id}", true)
    g = model.entities.add_group
    spacing = len / (num+1).to_f
    (1..num).each do |i|
      ox = start_pt[0]+vx[0]*spacing*i; oy = start_pt[1]+vx[1]*spacing*i
      p1=[ox-vx[0]*pil_w/2+vout[0]*0, oy-vx[1]*pil_w/2+vout[1]*0, 0]
      p2=[ox+vx[0]*pil_w/2+vout[0]*0, oy+vx[1]*pil_w/2+vout[1]*0, 0]
      p3=[p2[0], p2[1], bh]
      p4=[p1[0], p1[1], bh]
      pf = g.entities.add_face(p1,p2,p3,p4)
      pf.pushpull(depth_out) rescue nil
    end
    g.name = "Pilasters"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR pilasters: #{e.message}"
  end

  # ============================================================
  # SHUTTERS - flanking windows
  # ============================================================

  def self.add_shutters(id, face_name, xo, zo, win_w, win_h)
    return unless (b = @@blocks[id])
    bx, by, bw, bd = b[:x], b[:y], b[:w], b[:d]
    case face_name
    when "front" then p_base=[bx+xo,by,zo]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then p_base=[bx+bw-xo,by+bd,zo]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then p_base=[bx,by+bd-xo,zo]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then p_base=[bx+bw,by+xo,zo]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return
    end
    model = Sketchup.active_model
    model.start_operation("Shutters #{id}", true)
    g = model.entities.add_group
    sw = win_w * 0.45
    [-1, 1].each do |side|
      off = (side == -1 ? -sw-1.0 : win_w+1.0)
      sp1=[p_base[0]+vx[0]*off, p_base[1]+vx[1]*off, zo]
      sp2=[sp1[0]+vx[0]*sw, sp1[1]+vx[1]*sw, zo]
      sp3=[sp2[0], sp2[1], zo+win_h]
      sp4=[sp1[0], sp1[1], zo+win_h]
      shf = g.entities.add_face(sp1,sp2,sp3,sp4)
      shf.pushpull(1.5) rescue nil
    end
    g.name = "Shutters"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR shutters: #{e.message}"
  end

  # ============================================================
  # PEDIMENT - triangular ornament over door/window
  # ============================================================

  def self.add_pediment(id, face_name, xo, w, zo, ped_h)
    return unless (b = @@blocks[id])
    bx, by, bw, bd = b[:x], b[:y], b[:w], b[:d]
    case face_name
    when "front" then p1=[bx+xo,by,zo]; vx=[1,0,0]; vy=[0,0,1]; vn=[0,-1,0]
    when "back"  then p1=[bx+bw-xo,by+bd,zo]; vx=[-1,0,0]; vy=[0,0,1]; vn=[0,1,0]
    when "left"  then p1=[bx,by+bd-xo,zo]; vx=[0,-1,0]; vy=[0,0,1]; vn=[-1,0,0]
    when "right" then p1=[bx+bw,by+xo,zo]; vx=[0,1,0]; vy=[0,0,1]; vn=[1,0,0]
    else return
    end
    p2=[p1[0]+vx[0]*w,p1[1]+vx[1]*w,p1[2]]
    apex=[p1[0]+vx[0]*w/2,p1[1]+vx[1]*w/2, zo+ped_h]
    model = Sketchup.active_model
    model.start_operation("Pediment #{id}", true)
    g = model.entities.add_group
    pf = g.entities.add_face(p1, p2, apex)
    pf.pushpull(3) rescue nil
    g.name = "Pediment"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR pediment: #{e.message}"
  end

  # ============================================================
  # QUOINS - corner block details
  # ============================================================

  def self.add_quoins(id, block_w, block_h, spacing, depth_out)
    return unless (b = @@blocks[id])
    x, y, w, d, h = b[:x], b[:y], b[:w], b[:d], b[:h]
    block_w = 12.0 if block_w.to_f <= 0
    block_h = 8.0 if block_h.to_f <= 0
    spacing = 4.0 if spacing.to_f <= 0
    depth_out = 2.0 if depth_out.to_f <= 0
    model = Sketchup.active_model
    model.start_operation("Quoins #{id}", true)
    g = model.entities.add_group
    # 4 corners: front-left, front-right, back-left, back-right
    corners = [[x,y,[1,0],[0,-1]], [x+w,y,[-1,0],[0,-1]], [x,y+d,[1,0],[0,1]], [x+w,y+d,[-1,0],[0,1]]]
    z_cursor = 0
    while z_cursor < h
      corners.each do |cx2, cy2, vlong, vshort|
        # Alternating long and short
        is_long = ((z_cursor / (block_h+spacing)).floor % 2 == 0)
        bw2 = is_long ? block_w : block_w*0.6; bd2 = is_long ? block_w*0.6 : block_w
        qf = g.entities.add_face(
          [cx2, cy2, z_cursor],
          [cx2+vlong[0]*bw2, cy2+vlong[1]*bw2, z_cursor],
          [cx2+vlong[0]*bw2, cy2+vlong[1]*bw2, z_cursor+block_h],
          [cx2, cy2, z_cursor+block_h]
        )
        qf.pushpull(depth_out) rescue nil
      end
      z_cursor += block_h + spacing
    end
    g.name = "Quoins"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR quoins: #{e.message}"
  end

  # ============================================================
  # STEPS - refined with nosing
  # ============================================================

  def self.build_steps(id, face_name, xo, w, num_steps)
    return unless (b = @@blocks[id])
    bx, by, bw, bd = b[:x], b[:y], b[:w], b[:d]
    case face_name
    when "front" then bp=[bx+xo,by,0]; vw=[1,0,0]; vout=[0,-1,0]
    when "back"  then bp=[bx+bw-xo,by+bd,0]; vw=[-1,0,0]; vout=[0,1,0]
    when "left"  then bp=[bx,by+bd-xo,0]; vw=[0,-1,0]; vout=[-1,0,0]
    when "right" then bp=[bx+bw,by+xo,0]; vw=[0,1,0]; vout=[1,0,0]
    else return
    end
    model = Sketchup.active_model
    model.start_operation("Steps #{id}", true)
    g = model.entities.add_group
    step_h = 7.0; step_d = 12.0; nosing = 1.5
    (1..num_steps).each do |i|
      sy = step_d * i; sz = step_h * (num_steps - i + 1)
      p1=[bp[0]+vout[0]*sy,bp[1]+vout[1]*sy,0]
      p2=[p1[0]+vw[0]*w,p1[1]+vw[1]*w,0]
      p3=[p2[0],p2[1],sz]; p4=[p1[0],p1[1],sz]
      f = g.entities.add_face(p1,p2,p3,p4)
      f.pushpull(-(step_d+nosing)) rescue nil
    end
    b[:features] << g
    model.commit_operation
  rescue => e; "ERROR steps: #{e.message}"
  end

  # ============================================================
  # GROUND PLANE with path
  # ============================================================

  def self.add_ground_plane(cx, cy, total_w, total_d, path_w)
    model = Sketchup.active_model
    model.start_operation("Ground", true)
    g = model.entities.add_group
    gf = g.entities.add_face([cx,cy,0],[cx+total_w,cy,0],[cx+total_w,cy+total_d,0],[cx,cy+total_d,0])
    gf.reverse! if gf.normal.z < 0
    gf.pushpull(-2)
    # Center path
    px = cx + (total_w - path_w)/2.0
    pf = g.entities.add_face([px,cy,0],[px+path_w,cy,0],[px+path_w,cy+total_d*0.4,0],[px,cy+total_d*0.4,0])
    pf.reverse! if pf.normal.z < 0
    pf.pushpull(1) rescue nil
    g.name = "Ground"
    model.commit_operation
  rescue => e; "ERROR ground: #{e.message}"
  end
  def self.add_ridge_finial(id, direction)
    return unless (b = @@blocks[id])
    return unless (rg = b[:roof_group])
    x, y, w, d, h = b[:x], b[:y], b[:w], b[:d], b[:h]
    z = b[:z] || 0.0
    model = Sketchup.active_model
    model.start_operation("Finial #{id}", true)
    g = model.entities.add_group
    # Place at ridge apex
    fx = x + w/2.0; fy = y + d/2.0
    # Find approximate apex height
    fz = z + h + (direction == "front-back" ? (w/2.0)*Math.tan(35*Math::PI/180) : (d/2.0)*Math.tan(35*Math::PI/180))
    fz -= 10 # offset for roof thickness
    r = 4.0
    # Sphere-like finial (octagonal approximation)
    base_f = g.entities.add_face([fx-r,fy-r,fz],[fx+r,fy-r,fz],[fx+r,fy+r,fz],[fx-r,fy+r,fz])
    base_f.pushpull(r*2) rescue nil
    tip_f = g.entities.add_face([fx-r/2,fy-r/2,fz+r*2],[fx+r/2,fy-r/2,fz+r*2],[fx+r/2,fy+r/2,fz+r*2],[fx-r/2,fy+r/2,fz+r*2])
    tip_f.pushpull(r*3) rescue nil
    g.name = "Finial"; b[:features] << g
    model.commit_operation
  rescue => e; "ERROR finial: #{e.message}"
  end

  # ============================================================
  # APPLY MATERIALS
  # ============================================================

  def self.apply_materials(body_color, roof_color, trim_color, door_color, accent_color="#808080", ground_color="#5A7247", garage_door_color="#FFFFFF", roof_tex_path="", wall_tex_path="")
    model = Sketchup.active_model
    model.start_operation("Materials", true)
    mats = model.materials
    mb = mats.add("BodyColor"); mb.color = parse_color(body_color, [240,232,215])
    if wall_tex_path && wall_tex_path != "" && File.exist?(wall_tex_path)
      mb.texture = wall_tex_path
      mb.texture.size = [360.0, 360.0]
    end
    mr = mats.add("RoofColor"); mr.color = parse_color(roof_color, [95, 88, 80])
    if roof_tex_path && roof_tex_path != "" && File.exist?(roof_tex_path)
      mr.texture = roof_tex_path
      mr.texture.size = [36.0, 36.0]
    end
    mt = mats.add("TrimColor"); mt.color = parse_color(trim_color, [255,255,255])
    md = mats.add("DoorColor"); md.color = parse_color(door_color, [120,75,35])
    mgd = mats.add("GarageDoorColor"); mgd.color = parse_color(garage_door_color, [255,255,255])
    ma = mats.add("AccentColor"); ma.color = parse_color(accent_color, [128,128,128])
    mgnd = mats.add("GroundColor"); mgnd.color = parse_color(ground_color, [90,114,71])
    mg = mats.add("GlassColor"); mg.color = [140,195,225]; mg.alpha = 0.6

    @@blocks.each do |id, b|
      b[:group].entities.grep(Sketchup::Face).each {|f| f.material=mb; f.back_material=mb} if b[:group]
      b[:gable_faces].each {|gf| gf.material=mb; gf.back_material=mb if gf.valid?}

      if b[:roof_group]
        b[:roof_group].entities.grep(Sketchup::Face).each do |f|
          next if b[:gable_faces].include?(f)
          f.material = mr; f.back_material = mr
        end
      end

      b[:features].each do |fg|
        next unless fg.respond_to?(:entities)
        
        # 1. Paint subgroups first (like PorchRoof, VerandaRoof)
        fg.entities.grep(Sketchup::Group).each do |sg|
          if sg.name =~ /Roof/i
            sg.entities.grep(Sketchup::Face).each do |f|
              f.material = mr; f.back_material = mr
            end
          end
        end

        # 2. Paint loose faces based on the parent group name
        fg.entities.grep(Sketchup::Face).each do |f|
          next if f.material # SKIP if Parametric generator already painted it!
          
          # If it has no material, paint based on regex match of group name
          case fg.name
          when /GarageDoor/ then f.material = mgd
          when /Door/       then f.material = md
          when /Window/     then f.material = mt
          when /Column/, /Porch/, /Veranda/ then f.material = mb
          when /Pilaster/,/BeltCourse/,/Baseboard/,/Arch/,/Pediment/ then f.material = mt
          when /Balcony/,/Steps/ then f.material = ma
          when /Ground/ then f.material = mgnd
          when /Shutter/    then f.material = md
          when /Quoin/      then f.material = mb
          when /Canopy/, /Dormer/ then f.material = mt
          else; f.material = mt
          end
        end
      end
      end # @@blocks.each

      # FINAL PASS: Ensure no unpainted faces remain!
      model.entities.grep(Sketchup::Group).each do |ent|
        # 1. Paint unpainted faces in the main group
        ent.entities.grep(Sketchup::Face).each do |f|
          next if f.material
          if f.normal.z > 0.9 # Upward facing flat face
            f.material = mr; f.back_material = mr
          else
            f.material = mb; f.back_material = mb
          end
        end
        # 2. Paint unpainted faces in subgroups
        ent.entities.grep(Sketchup::Group).each do |sg|
          sg.entities.grep(Sketchup::Face).each do |f|
            next if f.material
            if sg.name =~ /Roof/i || f.normal.z > 0.9
              f.material = mr; f.back_material = mr
            else
              f.material = mb; f.back_material = mb
            end
          end
        end
      end

      model.commit_operation
      "Materials applied."
    rescue => e
      "ERROR apply_materials: #{e.message}\n#{e.backtrace.join(%Q{\n})}"
  end

  # ============================================================
  # CAMERA
  # ============================================================

  def self.set_camera(azimuth=0.0, elevation=15.0, fov=45.0)
    model = Sketchup.active_model
    view = model.active_view
    bounds = model.bounds
    center = bounds.center
    
    diagonal = bounds.diagonal
    diagonal = 500.0 if diagonal < 100.0
    distance = diagonal * 1.5
    
    azi_rad = azimuth * Math::PI / 180.0
    ele_rad = elevation * Math::PI / 180.0
    
    dx = distance * Math.sin(azi_rad) * Math.cos(ele_rad)
    dy = -distance * Math.cos(azi_rad) * Math.cos(ele_rad)
    # If elevation is positive (looking UP), camera must be BELOW center
    dz = distance * Math.sin(ele_rad)
    
    eye = [center.x + dx, center.y + dy, center.z - dz]
    target = center
    up = [0, 0, 1]
    
    camera = Sketchup::Camera.new(eye, target, up)
    camera.fov = fov
    
    view.camera = camera
    view.zoom_extents
    "Camera set to azimuth=#{azimuth}, elevation=#{elevation}, fov=#{fov}"
  end

  # ============================================================
  # ADVANCED GEOMETRY MERGING (v4.0)
  # ============================================================
  def self.merge_geometry
    model = Sketchup.active_model
    roof_groups = @@blocks.values.map { |b| b[:roof_group] }.compact
    wall_groups = @@blocks.values.map { |b| b[:group] }.compact
    
    model.start_operation("Merge Geometry (v4.0)", true)
    
    # 1. Intersect roofs with roofs (Valley / Hip lines)
    roof_groups.each do |rg1|
      roof_groups.each do |rg2|
        next if rg1 == rg2
        rg1.entities.intersect_with(false, rg1.transformation, rg1.entities, 
                                    rg2.transformation, false, rg2)
      end
    end
    
    # 2. Intersect roofs with walls (Trim lines)
    wall_groups.each do |wg|
      roof_groups.each do |rg|
        wg.entities.intersect_with(false, wg.transformation, wg.entities, 
                                   rg.transformation, false, rg)
      end
    end
    
    model.commit_operation
    "Geometry Merged (Valleys & Wall Trims)"
  rescue => e
    "ERROR merge_geometry: #{e.message}"
  end

  # ============================================================
  # PROCEDURAL SIDING (v4.2)
  # ============================================================
  def self.apply_siding(spacing=8.0)
    model = Sketchup.active_model
    wall_groups = @@blocks.values.map { |b| b[:group] }.compact
    return "No wall groups" if wall_groups.empty?
    
    model.start_operation("Apply Siding", true)
    
    bounds = Geom::BoundingBox.new
    wall_groups.each { |wg| bounds.add(wg.bounds) }
    max_z = bounds.max.z
    min_z = bounds.min.z
    
    temp_group = model.active_entities.add_group
    
    b_min = bounds.min
    b_max = bounds.max
    
    z = min_z + spacing
    while z < max_z
      p1 = [b_min.x - 100, b_min.y - 100, z]
      p2 = [b_max.x + 100, b_min.y - 100, z]
      p3 = [b_max.x + 100, b_max.y + 100, z]
      p4 = [b_min.x - 100, b_max.y + 100, z]
      temp_group.entities.add_face(p1, p2, p3, p4) rescue nil
      z += spacing
    end
    
    wall_groups.each do |wg|
      wg.entities.intersect_with(false, wg.transformation, wg.entities, 
                                 temp_group.transformation, false, temp_group)
    end
    
    temp_group.erase!
    model.commit_operation
    "Siding applied with spacing #{spacing}"
  rescue => e
    "ERROR apply_siding: #{e.message}"
  end

  # ============================================================
  # ASIAN COURTYARD EXTENSION (v5.0)
  # ============================================================
  
  def self.add_platform(x, y, w, d, height, has_planters=false, paving_grid=false)
    model = Sketchup.active_model
    model.start_operation("Add Platform", true)
    g = model.active_entities.add_group
    
    # 1. Base Platform
    f = g.entities.add_face([x,y,0], [x+w,y,0], [x+w,y+d,0], [x,y+d,0])
    f.reverse! if f.normal.z < 0
    f.pushpull(height) rescue nil
    
    mats = model.materials
    mp = mats["PlatformColor"] || mats.add("PlatformColor")
    mp.color = [180, 180, 185]
    g.entities.grep(Sketchup::Face).each { |face| face.material = mp; face.back_material = mp }
    model.commit_operation
  end

  # ============================================================
  # TIMBER FRAMING (v10.1)
  # ============================================================
  def self.add_timber_framing(id, face_name, style="cross_brace")
    return unless (b = @@blocks[id])
    bx, by, bw, bd = b[:x], b[:y], b[:w], b[:d]
    z = b[:z] || 0.0
    case face_name
    when "front" then p1=[bx,by,z]; p2=[bx+bw,by,z]; p3=[bx+bw,by,z+b[:h]]; p4=[bx,by,z+b[:h]]; vout=[0,-1,0]
    when "back"  then p1=[bx+bw,by+bd,z]; p2=[bx,by+bd,z]; p3=[bx,by+bd,z+b[:h]]; p4=[bx+bw,by+bd,z+b[:h]]; vout=[0,1,0]
    when "left"  then p1=[bx,by+bd,z]; p2=[bx,by,z]; p3=[bx,by,z+b[:h]]; p4=[bx,by+bd,z+b[:h]]; vout=[-1,0,0]
    when "right" then p1=[bx+bw,by,z]; p2=[bx+bw,by+bd,z]; p3=[bx+bw,by+bd,z+b[:h]]; p4=[bx+bw,by,z+b[:h]]; vout=[1,0,0]
    else return
    end
    p1 = Geom::Point3d.new(p1); p2 = Geom::Point3d.new(p2); p3 = Geom::Point3d.new(p3); p4 = Geom::Point3d.new(p4)
    model = Sketchup.active_model
    model.start_operation("TimberFraming #{id}", true)
    g = model.entities.add_group
    
    t = 2.0  # depth
    w = 6.0  # width
    
    # helper: draw a straight beam between two points
    draw_beam = lambda do |ptA, ptB|
      v = ptA.vector_to(ptB)
      return unless v.valid?
      v.normalize!
      perp = v.cross(vout)
      bf = g.entities.add_face(
        ptA.offset(perp, w/2.0),
        ptA.offset(perp, -w/2.0),
        ptB.offset(perp, -w/2.0),
        ptB.offset(perp, w/2.0)
      )
      bf.reverse! if bf.normal.dot(vout) < 0
      bf.pushpull(t) rescue nil
    end

    draw_beam.call(p1, p2) # bottom plate
    draw_beam.call(p4, p3) # top plate
    draw_beam.call(p1, p4) # left post
    draw_beam.call(p2, p3) # right post

    w_val = (face_name == "front" || face_name == "back") ? bw : bd
    h_val = b[:h]
    
    num_panels = [ (w_val / 48.0).round, 1 ].max
    panel_w = w_val / num_panels.to_f
    
    # Draw intermediate vertical posts
    (1...num_panels).each do |i|
      vx = (p2 - p1).normalize
      bp = p1 + [vx.x * i * panel_w, vx.y * i * panel_w, vx.z * i * panel_w]
      tp = p4 + [vx.x * i * panel_w, vx.y * i * panel_w, vx.z * i * panel_w]
      draw_beam.call(bp, tp)
    end
    
    # Draw diagonals or other styles within each panel
    (0...num_panels).each do |i|
      vx = (p2 - p1).normalize
      p1_p = p1 + [vx.x * i * panel_w, vx.y * i * panel_w, vx.z * i * panel_w]
      p2_p = p1 + [vx.x * (i+1) * panel_w, vx.y * (i+1) * panel_w, vx.z * (i+1) * panel_w]
      p4_p = p4 + [vx.x * i * panel_w, vx.y * i * panel_w, vx.z * i * panel_w]
      p3_p = p4 + [vx.x * (i+1) * panel_w, vx.y * (i+1) * panel_w, vx.z * (i+1) * panel_w]
      
      case style
      when "cross_brace"
        draw_beam.call(p1_p, p3_p)
        draw_beam.call(p2_p, p4_p)
      when "single_brace"
        draw_beam.call((i.even? ? p1_p : p2_p), (i.even? ? p3_p : p4_p))
      when "half_timbered"
        mid_p12 = Geom::Point3d.new((p1_p.x+p2_p.x)/2, (p1_p.y+p2_p.y)/2, (p1_p.z+p2_p.z)/2)
        mid_p43 = Geom::Point3d.new((p4_p.x+p3_p.x)/2, (p4_p.y+p3_p.y)/2, (p4_p.z+p3_p.z)/2)
        draw_beam.call(mid_p12, mid_p43)
      end
    end
    
    g.name = "TimberFraming"
    b[:features] << g
    model.commit_operation
  rescue => e
    "ERROR timber framing: #{e.message}"
  end

end
